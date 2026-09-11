from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptRule:
    canonical: str
    aliases: tuple[str, ...]
    statement: str
    instant: bool
    rationale: str


RULES = (
    ConceptRule(
        "revenue",
        ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"),
        "income_statement",
        False,
        "Explicit alias set; raw tag retained.",
    ),
    ConceptRule(
        "net_income", ("NetIncomeLoss",), "income_statement", False, "Direct us-gaap concept."
    ),
    ConceptRule(
        "gross_profit", ("GrossProfit",), "income_statement", False, "Direct us-gaap concept."
    ),
    ConceptRule(
        "operating_income",
        ("OperatingIncomeLoss",),
        "income_statement",
        False,
        "Direct us-gaap concept.",
    ),
    ConceptRule(
        "cash_and_equivalents",
        ("CashAndCashEquivalentsAtCarryingValue",),
        "balance_sheet",
        True,
        "Direct instant concept.",
    ),
    ConceptRule(
        "accounts_receivable",
        ("AccountsReceivableNetCurrent", "ReceivablesNetCurrent"),
        "balance_sheet",
        True,
        "Known alias variation.",
    ),
    ConceptRule(
        "inventory",
        ("InventoryNet", "InventoryFinishedGoodsNetOfReserves"),
        "balance_sheet",
        True,
        "Known filing-vintage/company variation.",
    ),
    ConceptRule("total_assets", ("Assets",), "balance_sheet", True, "Direct instant concept."),
    ConceptRule(
        "total_liabilities", ("Liabilities",), "balance_sheet", True, "Direct instant concept."
    ),
    ConceptRule(
        "stockholders_equity",
        (
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        ),
        "balance_sheet",
        True,
        "NCI presentation varies.",
    ),
    ConceptRule(
        "cfo",
        ("NetCashProvidedByUsedInOperatingActivities",),
        "cash_flow",
        False,
        "Direct duration concept.",
    ),
    ConceptRule(
        "capex",
        ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
        "cash_flow",
        False,
        "Known taxonomy naming transition.",
    ),
)
ALIAS_TO_RULE = {a: r for r in RULES for a in r.aliases}


def resolve_concept(raw_concept: str) -> ConceptRule | None:
    return ALIAS_TO_RULE.get(raw_concept)
