import io
import unicodedata
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlmodel import select

from core.deps import CurrentUser, SessionDep
from models.account import Account
from models.investment import (
    Asset,
    AssetType,
    Investment,
    InvestmentOperation,
    OperationType,
)
from routers.accounts import get_owned_account
from schemas.investment import (
    AssetCreate,
    AssetPriceUpdate,
    AssetRead,
    BuyOrder,
    ImportResult,
    InvestmentPosition,
    InvestmentProgress,
    InvestmentRead,
    InvestmentSummary,
    ProgressPoint,
    SellOrder,
    SplitOrder,
)

router = APIRouter(prefix="/investments", tags=["investments"])


def _get_owned_investment(
    investment_id: int, current_user: CurrentUser, session: SessionDep
) -> Investment:
    """Fetch an investment and verify ownership through its account."""
    investment = session.get(Investment, investment_id)
    if investment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Investment not found"
        )
    account = session.get(Account, investment.account_id)
    if account is None or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Investment not found"
        )
    return investment


def _replay_operations(operations) -> tuple[float, float]:
    """Replay an operation log in order; returns (shares, avg_buy_price)."""
    shares = 0.0
    avg_price = 0.0
    for op in operations:
        if op.type == OperationType.split:
            shares *= op.shares
            if op.shares:
                avg_price /= op.shares
        elif op.type == OperationType.buy:
            total = shares + op.shares
            avg_price = (shares * avg_price + op.shares * op.price) / total
            shares = total
        else:  # sell: shares drop, cost basis per share unchanged
            shares -= op.shares
    return shares, avg_price


def _recompute_position(investment: Investment, session: SessionDep) -> None:
    """Rebuild shares/avg_buy_price from the full operation log. Needed whenever
    operations are inserted out of order or a split lands mid-history."""
    operations = session.exec(
        select(InvestmentOperation)
        .where(InvestmentOperation.investment_id == investment.id)
        .order_by(InvestmentOperation.date, InvestmentOperation.id)
    ).all()
    investment.shares, investment.avg_buy_price = _replay_operations(operations)
    session.add(investment)


def _open_positions(current_user: CurrentUser, session: SessionDep) -> list[Investment]:
    return session.exec(
        select(Investment)
        .join(Account, Account.id == Investment.account_id)
        .where(Account.user_id == current_user.id)
        .where(Investment.closed_at == None)  # noqa: E711
    ).all()


# --- Assets ---------------------------------------------------------------


@router.get("/assets", response_model=list[AssetRead])
def list_assets(current_user: CurrentUser, session: SessionDep):
    return session.exec(select(Asset)).all()


@router.post("/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(data: AssetCreate, current_user: CurrentUser, session: SessionDep):
    existing = session.exec(
        select(Asset).where(Asset.ticker == data.ticker)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset with this ticker already exists",
        )
    asset = Asset(**data.model_dump())
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


# --- Positions ------------------------------------------------------------


@router.get("/", response_model=list[InvestmentRead])
def list_investments(current_user: CurrentUser, session: SessionDep):
    """Open positions for the current user."""
    return _open_positions(current_user, session)


@router.get("/summary", response_model=InvestmentSummary)
def investments_summary(current_user: CurrentUser, session: SessionDep):
    positions = _open_positions(current_user, session)

    enriched: list[InvestmentPosition] = []
    total_invested = 0.0
    for inv in positions:
        asset = session.get(Asset, inv.asset_id)
        invested = inv.shares * inv.avg_buy_price
        total_invested += invested
        enriched.append(
            InvestmentPosition(
                id=inv.id,
                account_id=inv.account_id,
                asset=AssetRead.model_validate(asset, from_attributes=True),
                shares=inv.shares,
                avg_buy_price=inv.avg_buy_price,
                invested=invested,
                currency=inv.currency,
            )
        )

    return InvestmentSummary(
        total_invested=total_invested,
        open_positions=len(enriched),
        positions=enriched,
    )


@router.post("/", response_model=InvestmentRead, status_code=status.HTTP_201_CREATED)
def buy(order: BuyOrder, current_user: CurrentUser, session: SessionDep):
    """Execute a buy: opens a new position or adds to an existing open one,
    recalculating the weighted average buy price."""
    get_owned_account(order.account_id, current_user, session)

    asset = session.get(Asset, order.asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    if order.shares <= 0 or order.price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares must be positive and price non-negative",
        )

    investment = session.exec(
        select(Investment)
        .where(Investment.account_id == order.account_id)
        .where(Investment.asset_id == order.asset_id)
        .where(Investment.closed_at == None)  # noqa: E711
    ).first()

    if investment is None:
        investment = Investment(
            account_id=order.account_id,
            asset_id=order.asset_id,
            currency=order.currency,
        )
        session.add(investment)
        session.flush()

    operation = InvestmentOperation(
        investment_id=investment.id,
        type=OperationType.buy,
        shares=order.shares,
        price=order.price,
        amount=order.amount,
        fees=order.fees,
        note=order.note,
        date=order.date,
    )
    session.add(operation)
    _recompute_position(investment, session)
    session.commit()
    session.refresh(investment)
    return investment


@router.post("/{investment_id}/sell", response_model=InvestmentRead)
def sell(
    investment_id: int,
    order: SellOrder,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Execute a sell: reduces shares; closes the position when it hits zero."""
    investment = _get_owned_investment(investment_id, current_user, session)

    if investment.closed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position is already closed",
        )
    if order.shares <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares must be positive",
        )
    if order.shares > investment.shares:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sell more shares than currently held",
        )

    operation = InvestmentOperation(
        investment_id=investment.id,
        type=OperationType.sell,
        shares=order.shares,
        price=order.price,
        amount=order.amount,
        fees=order.fees,
        note=order.note,
        date=order.date,
    )
    session.add(operation)
    _recompute_position(investment, session)
    if investment.shares <= 1e-9:
        investment.shares = 0.0
        investment.closed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(investment)
    return investment


@router.patch("/assets/{asset_id}/price", response_model=AssetRead)
def update_asset_price(
    asset_id: int,
    data: AssetPriceUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Record the current market price of an asset (assets are shared)."""
    asset = session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    if data.price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Price must be non-negative"
        )
    asset.last_price = data.price
    asset.last_price_at = datetime.now(timezone.utc)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


# --- XLSX import ------------------------------------------------------------

# Expected columns (header row 1). "Reason", "Cantidad" and "Comisión" are
# optional; computed columns (Acumulado, Valor Cartera, Rendimiento) are ignored.
_XLSX_COLUMNS = {
    "isin": "isin",
    "import": "amount",
    "price": "price",
    "date": "date",
    "reason": "note",
    "cantidad": "shares",
    "comision": "fees",
}


def _norm_header(value: str) -> str:
    """'Comisión (€)' -> 'comision', 'Cantidad (acciones)' -> 'cantidad'."""
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return text.strip().lower().split("(")[0].strip()


def _parse_xlsx_rows(content: bytes) -> list[dict]:
    try:
        import openpyxl

        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a readable .xlsx workbook",
        )

    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = next(rows, None)
    if header is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Workbook is empty"
        )

    fields: dict[int, str] = {}
    for idx, cell in enumerate(header):
        if not isinstance(cell, str) or "%" in cell:
            continue  # 'Comisión (%)' is derived; only 'Comisión (€)' is data
        field = _XLSX_COLUMNS.get(_norm_header(cell))
        if field is not None and field not in fields.values():
            fields[idx] = field

    missing = {"isin", "amount", "price", "date"} - set(fields.values())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required columns: {', '.join(sorted(missing))}. "
            "Expected headers: ISIN, Import, Price, Date, Reason, "
            "Cantidad (acciones), Comisión (€)",
        )

    parsed = []
    for row in rows:
        record = {field: row[idx] if idx < len(row) else None for idx, field in fields.items()}
        if all(v is None for v in record.values()):
            continue  # blank row
        parsed.append(record)
    return parsed


@router.post("/import/xlsx", response_model=ImportResult)
def import_xlsx(
    current_user: CurrentUser,
    session: SessionDep,
    account_id: int = Form(...),
    file: UploadFile = File(...),
):
    """Import buy operations from an Inv-format spreadsheet into an account.

    Re-importing the same file is safe: rows whose (asset, date, shares, price)
    already exist are skipped.
    """
    get_owned_account(account_id, current_user, session)
    records = _parse_xlsx_rows(file.file.read())

    imported, skipped = 0, 0
    errors: list[str] = []
    touched_investments: dict[int, Investment] = {}

    for line_no, rec in enumerate(records, start=2):
        try:
            isin = str(rec["isin"]).strip()
            amount = float(rec["amount"])
            price = float(rec["price"])
            raw_date = rec["date"]
            op_date = raw_date.date() if isinstance(raw_date, datetime) else raw_date
            shares = float(rec["shares"]) if rec.get("shares") else amount / price
            fees = abs(float(rec["fees"])) if rec.get("fees") else 0.0
            note = str(rec["note"]).strip() if rec.get("note") else None
            if not isin or amount <= 0 or price <= 0 or shares <= 0 or op_date is None:
                raise ValueError("ISIN, Import, Price and Date must be present and positive")
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(f"Row {line_no}: {exc}")
            continue

        asset = session.exec(select(Asset).where(Asset.isin == isin)).first()
        if asset is None:
            asset = Asset(ticker=isin, isin=isin, name=isin, type=AssetType.etf)
            session.add(asset)
            session.flush()

        investment = session.exec(
            select(Investment)
            .where(Investment.account_id == account_id)
            .where(Investment.asset_id == asset.id)
            .where(Investment.closed_at == None)  # noqa: E711
        ).first()
        if investment is None:
            investment = Investment(
                account_id=account_id, asset_id=asset.id, shares=0.0, avg_buy_price=0.0
            )
            session.add(investment)
            session.flush()

        duplicate = session.exec(
            select(InvestmentOperation)
            .where(InvestmentOperation.investment_id == investment.id)
            .where(InvestmentOperation.date == op_date)
            .where(InvestmentOperation.shares == shares)
            .where(InvestmentOperation.price == price)
        ).first()
        if duplicate:
            skipped += 1
            continue

        session.add(
            InvestmentOperation(
                investment_id=investment.id,
                type=OperationType.buy,
                shares=shares,
                price=price,
                amount=amount,
                fees=fees,
                note=note,
                date=op_date,
            )
        )
        # The newest imported price is our best known market price.
        if asset.last_price_at is None or asset.last_price_at.date() <= op_date:
            asset.last_price = price
            asset.last_price_at = datetime(
                op_date.year, op_date.month, op_date.day, tzinfo=timezone.utc
            )
            session.add(asset)
        touched_investments[investment.id] = investment
        imported += 1

    for investment in touched_investments.values():
        _recompute_position(investment, session)
    session.commit()
    return ImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
        investment_ids=sorted(touched_investments),
    )


@router.post("/{investment_id}/split", response_model=InvestmentRead)
def register_split(
    investment_id: int,
    order: SplitOrder,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Register a stock split (e.g. ratio=25 for 25:1) and rebuild the position."""
    investment = _get_owned_investment(investment_id, current_user, session)
    if order.ratio <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Ratio must be positive"
        )

    session.add(
        InvestmentOperation(
            investment_id=investment.id,
            type=OperationType.split,
            shares=order.ratio,
            price=0.0,
            note=order.note,
            date=order.date,
        )
    )
    _recompute_position(investment, session)

    # A last known price recorded before the split is in pre-split units.
    asset = session.get(Asset, investment.asset_id)
    if asset.last_price is not None and (
        asset.last_price_at is None or asset.last_price_at.date() < order.date
    ):
        asset.last_price /= order.ratio
        session.add(asset)

    session.commit()
    session.refresh(investment)
    return investment


@router.get("/{investment_id}/progress", response_model=InvestmentProgress)
def investment_progress(
    investment_id: int, current_user: CurrentUser, session: SessionDep
):
    """Time series of the position: after each operation, invested capital,
    cumulative shares and the position value at that day's price."""
    investment = _get_owned_investment(investment_id, current_user, session)
    asset = session.get(Asset, investment.asset_id)
    operations = session.exec(
        select(InvestmentOperation)
        .where(InvestmentOperation.investment_id == investment_id)
        .order_by(InvestmentOperation.date, InvestmentOperation.id)
    ).all()

    points: list[ProgressPoint] = []
    invested = 0.0
    shares = 0.0
    total_fees = 0.0
    for op in operations:
        if op.type == OperationType.split:
            # Value is unchanged by a split; no point emitted.
            shares *= op.shares
            continue
        cash = op.amount if op.amount is not None else op.shares * op.price
        if op.type == OperationType.buy:
            invested += cash
            shares += op.shares
        else:
            invested -= cash
            shares -= op.shares
        total_fees += op.fees
        value = shares * op.price
        points.append(
            ProgressPoint(
                date=op.date,
                invested=invested,
                shares=shares,
                price=op.price,
                value=value,
                return_pct=(value - invested) / invested if invested > 0 else 0.0,
                note=op.note,
            )
        )

    current_value = None
    current_return = None
    if asset.last_price is not None and shares > 0:
        current_value = shares * asset.last_price
        if invested > 0:
            current_return = (current_value - invested) / invested

    return InvestmentProgress(
        investment_id=investment_id,
        asset=AssetRead.model_validate(asset, from_attributes=True),
        points=points,
        total_invested=invested,
        total_fees=total_fees,
        current_value=current_value,
        current_return_pct=current_return,
    )


@router.get("/{investment_id}/history")
def investment_history(
    investment_id: int, current_user: CurrentUser, session: SessionDep
):
    """All buy/sell operations for a position, oldest first."""
    _get_owned_investment(investment_id, current_user, session)
    return session.exec(
        select(InvestmentOperation)
        .where(InvestmentOperation.investment_id == investment_id)
        .order_by(InvestmentOperation.date, InvestmentOperation.id)
    ).all()
