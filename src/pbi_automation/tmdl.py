from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pbi_automation.io_util import write_json, write_text
from pbi_automation.models import DashboardSpec, stable_guid
from pbi_automation.platform import write_platform


@dataclass
class ColumnDef:
    name: str
    data_type: str
    source_column: str | None = None
    summarize_by: str = "none"
    format_string: str | None = None
    is_key: bool = False
    is_hidden: bool = False
    is_unique: bool = False


@dataclass
class MeasureDef:
    name: str
    expression: str
    format_string: str | None = None


@dataclass
class TableDef:
    name: str
    entity: str
    columns: list[ColumnDef]
    measures: list[MeasureDef] = field(default_factory=list)


@dataclass
class RelationshipDef:
    name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str


NORTHWIND_TABLES: list[TableDef] = [
    TableDef(
        name="Customers",
        entity="Customers",
        columns=[
            ColumnDef("CustomerID", "string", "CustomerID", is_key=True, is_unique=True),
            ColumnDef("CompanyName", "string", "CompanyName"),
            ColumnDef("City", "string", "City"),
            ColumnDef("Country", "string", "Country"),
        ],
    ),
    TableDef(
        name="Orders",
        entity="Orders",
        columns=[
            ColumnDef("OrderID", "int64", "OrderID", is_key=True, is_unique=True, format_string="0"),
            ColumnDef("CustomerID", "string", "CustomerID"),
            ColumnDef("OrderDate", "dateTime", "OrderDate", format_string="yyyy-mm-dd"),
            ColumnDef("Freight", "double", "Freight", summarize_by="sum", format_string="$#,0.00"),
            ColumnDef("ShipCountry", "string", "ShipCountry"),
        ],
    ),
    TableDef(
        name="Products",
        entity="Products",
        columns=[
            ColumnDef("ProductID", "int64", "ProductID", is_key=True, is_unique=True, format_string="0"),
            ColumnDef("ProductName", "string", "ProductName"),
            ColumnDef("UnitPrice", "double", "UnitPrice", summarize_by="sum", format_string="$#,0.00"),
        ],
    ),
    TableDef(
        name="Order_Details",
        entity="Order_Details",
        columns=[
            ColumnDef("OrderID", "int64", "OrderID", format_string="0"),
            ColumnDef("ProductID", "int64", "ProductID", format_string="0"),
            ColumnDef("UnitPrice", "double", "UnitPrice", summarize_by="none", format_string="$#,0.00"),
            ColumnDef("Quantity", "int64", "Quantity", summarize_by="sum", format_string="0"),
            ColumnDef("Discount", "double", "Discount", summarize_by="none", format_string="0%"),
        ],
        measures=[
            MeasureDef(
                name="Total Sales",
                expression=(
                    "SUMX('Order_Details', 'Order_Details'[UnitPrice] * "
                    "'Order_Details'[Quantity] * (1 - 'Order_Details'[Discount]))"
                ),
                format_string="$#,0.00",
            ),
            MeasureDef(
                name="Order Count",
                expression="DISTINCTCOUNT(Orders[OrderID])",
                format_string="#,0",
            ),
            MeasureDef(
                name="Avg Order Value",
                expression="DIVIDE([Total Sales], [Order Count])",
                format_string="$#,0.00",
            ),
        ],
    ),
]

NORTHWIND_RELATIONSHIPS = [
    RelationshipDef("Order_Details_Orders", "Order_Details", "OrderID", "Orders", "OrderID"),
    RelationshipDef("Order_Details_Products", "Order_Details", "ProductID", "Products", "ProductID"),
    RelationshipDef("Orders_Customers", "Orders", "CustomerID", "Customers", "CustomerID"),
]


def _lineage(*parts: str) -> str:
    return stable_guid("lineage", *parts)


def _indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(f"{pad}{line}" if line else "" for line in text.splitlines())


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _m_partition(url: str, entity: str) -> str:
    source = f"""let
    Source = OData.Feed("{url}/", null, [Implementation="2.0"]),
    Navigation = Source{{[Name="{entity}",Signature="table"]}}[Data]
in
    Navigation"""
    return _indent(source, 12)


def _render_column(table: str, column: ColumnDef) -> str:
    lines = [f"    column {column.name}"]
    lines.append(f"        dataType: {column.data_type}")
    if column.format_string:
        lines.append(f"        formatString: {_quote(column.format_string)}")
    if column.is_hidden:
        lines.append("        isHidden")
    if column.is_unique:
        lines.append("        isUnique")
    if column.is_key:
        lines.append("        isKey")
    if column.source_column:
        lines.append(f"        sourceColumn: {column.source_column}")
    lines.append(f"        summarizeBy: {column.summarize_by}")
    lines.append(f"        lineageTag: {_lineage(table, 'column', column.name)}")
    return "\n".join(lines)


def _render_measure(table: str, measure: MeasureDef) -> str:
    quoted = f"'{measure.name}'" if " " in measure.name else measure.name
    lines = [f"    measure {quoted} = {measure.expression}"]
    if measure.format_string:
        lines.append(f"        formatString: {_quote(measure.format_string)}")
    lines.append(f"        lineageTag: {_lineage(table, 'measure', measure.name)}")
    return "\n".join(lines)


def _render_table(spec: DashboardSpec, table: TableDef) -> str:
    parts = [
        f"table {table.name}",
        f"    lineageTag: {_lineage('table', table.name)}",
        "",
        f"    partition {table.name} = m",
        "        mode: import",
        "        source =",
        _m_partition(spec.source.url, table.entity),
        "",
    ]
    for column in table.columns:
        parts.append(_render_column(table.name, column))
        parts.append("")
    for measure in table.measures:
        parts.append(_render_measure(table.name, measure))
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _render_relationships() -> str:
    blocks = []
    for rel in NORTHWIND_RELATIONSHIPS:
        blocks.append(
            "\n".join(
                [
                    f"relationship {rel.name}",
                    "    fromCardinality: many",
                    "    toCardinality: one",
                    f"    fromColumn: {rel.from_table}.{rel.from_column}",
                    f"    toColumn: {rel.to_table}.{rel.to_column}",
                    f"    lineageTag: {_lineage('relationship', rel.name)}",
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def _render_model() -> str:
    refs = "\n".join(f"ref table {table.name}" for table in NORTHWIND_TABLES)
    query_order = ", ".join(f'"{table.name}"' for table in NORTHWIND_TABLES)
    return f"""model Model
    culture: en-US
    defaultPowerBIDataSourceVersion: powerBI_V3
    sourceQueryCulture: en-US
    dataAccessOptions
        legacyRedirects
        returnErrorValuesAsNull

annotation PBI_QueryOrder = [{query_order}]

{refs}
ref cultureInfo en-US
"""


def write_semantic_model(output_dir: Path, spec: DashboardSpec) -> Path:
    model_dir = output_dir / spec.semantic_model_dir_name
    definition = model_dir / "definition"
    tables_dir = definition / "tables"

    write_platform(
        model_dir,
        item_type="SemanticModel",
        display_name=spec.name,
        description=f"{spec.name} semantic model (Northwind OData)",
    )
    write_json(
        model_dir / "definition.pbism",
        {
            "$schema": (
                "https://developer.microsoft.com/json-schemas/fabric/item/"
                "semanticModel/definitionProperties/1.0.0/schema.json"
            ),
            "version": "4.2",
            "settings": {"qnaEnabled": True},
        },
    )
    write_text(definition / "database.tmdl", "database\n    compatibilityLevel: 1601\n")
    write_text(definition / "model.tmdl", _render_model())
    write_text(definition / "relationships.tmdl", _render_relationships())
    write_text(definition / "cultures" / "en-US.tmdl", "cultureInfo en-US\n")
    for table in NORTHWIND_TABLES:
        write_text(tables_dir / f"{table.name}.tmdl", _render_table(spec, table))
    return model_dir
