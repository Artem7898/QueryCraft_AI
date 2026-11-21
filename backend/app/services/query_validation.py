"""Check generated query syntax and dialect without running the query."""

import logging
from contextvars import ContextVar

from sqlglot import Dialect, ErrorLevel, TokenType, exp
from sqlglot.errors import SqlglotError
from tree_sitter import Language, Node, Parser
from tree_sitter_javascript import language

from app.models.schemas import DatabaseType

_SQL_DIALECTS = {
    DatabaseType.POSTGRESQL: "postgres",
    DatabaseType.MYSQL: "mysql",
    DatabaseType.SQLITE: "sqlite",
}
_SQL_STATEMENTS = (
    exp.Query,
    exp.DML,
    exp.DDL,
    exp.Alter,
    exp.Drop,
    exp.TruncateTable,
    exp.Values,
    exp.Show,
    exp.Describe,
    exp.Pragma,
    exp.Grant,
    exp.Revoke,
)
_MAX_QUERY_BYTES = 16 * 1024

_MONGO_LANGUAGE = Language(language())
_MONGO_OPERATIONS = frozenset(
    {
        b"aggregate",
        b"bulkWrite",
        b"count",
        b"countDocuments",
        b"createCollection",
        b"createIndex",
        b"createIndexes",
        b"deleteMany",
        b"deleteOne",
        b"distinct",
        b"drop",
        b"dropDatabase",
        b"dropIndex",
        b"dropIndexes",
        b"estimatedDocumentCount",
        b"find",
        b"findAndModify",
        b"findOne",
        b"findOneAndDelete",
        b"findOneAndReplace",
        b"findOneAndUpdate",
        b"getCollectionInfos",
        b"getCollectionNames",
        b"getIndexes",
        b"insertMany",
        b"insertOne",
        b"renameCollection",
        b"replaceOne",
        b"runCommand",
        b"stats",
        b"updateMany",
        b"updateOne",
    }
)
_MONGO_CHAIN_METHODS = frozenset(
    {
        b"batchSize",
        b"collation",
        b"comment",
        b"explain",
        b"getCollection",
        b"getSiblingDB",
        b"hasNext",
        b"hint",
        b"limit",
        b"maxTimeMS",
        b"next",
        b"project",
        b"skip",
        b"sort",
        b"toArray",
    }
)
_VALIDATING_SQL = ContextVar("validating_provider_sql", default=False)


class _ProviderSQLLogFilter(logging.Filter):
    """Keep SQLGlot's raw SQL diagnostics out of application logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not _VALIDATING_SQL.get()


logging.getLogger("sqlglot").addFilter(_ProviderSQLLogFilter())


class InvalidQueryOutput(ValueError):
    """The generated text does not match an accepted statement shape."""


def validate_query(query: str, db_type: DatabaseType) -> None:
    """Require one query or database statement in the selected dialect.

    Raises:
        InvalidQueryOutput: The result is empty, oversized, or unparsable.
    """
    try:
        source = query.encode()
    except UnicodeEncodeError as exc:
        raise InvalidQueryOutput("Invalid generated text encoding") from exc
    if not query.strip() or "\0" in query or len(source) > _MAX_QUERY_BYTES:
        raise InvalidQueryOutput("Invalid generated query size")
    if db_type is DatabaseType.MONGODB:
        _validate_mongo(source)
    else:
        _validate_sql(query, db_type)


def _validate_sql(query: str, db_type: DatabaseType) -> None:
    dialect = Dialect.get_or_raise(_SQL_DIALECTS[db_type])
    validating = _VALIDATING_SQL.set(True)
    try:
        tokens = dialect.tokenize(query)
        if db_type is not DatabaseType.POSTGRESQL and any(
            token.token_type is TokenType.DCOLON for token in tokens
        ):
            raise InvalidQueryOutput("Unexpected SQL cast syntax")
        parsed = dialect.parser(error_level=ErrorLevel.RAISE).parse(tokens, query)
        statements = [
            statement
            for statement in parsed
            if statement is not None and not isinstance(statement, exp.Semicolon)
        ]
        if len(statements) != 1 or not isinstance(statements[0], _SQL_STATEMENTS):
            raise InvalidQueryOutput("Expected one database statement")
        statement = statements[0]
        for expression in statement.walk():
            _validate_sql_expression(expression, db_type)
        dialect.generate(statement, unsupported_level=ErrorLevel.RAISE)
    except (SqlglotError, RecursionError) as exc:
        raise InvalidQueryOutput("Invalid SQL in selected dialect") from exc
    finally:
        _VALIDATING_SQL.reset(validating)


def _validate_sql_expression(expression: exp.Expr, db_type: DatabaseType) -> None:
    if isinstance(expression, exp.Command):
        raise InvalidQueryOutput("Unsupported SQL statement")
    if isinstance(expression, exp.Select) and not expression.expressions:
        if db_type is not DatabaseType.POSTGRESQL or not expression.args.get("from_"):
            raise InvalidQueryOutput("Incomplete SELECT")
    if isinstance(expression, exp.Update) and not expression.expressions:
        raise InvalidQueryOutput("Incomplete UPDATE")
    if (
        isinstance(expression, exp.Insert)
        and expression.expression is None
        and not expression.args.get("default")
    ):
        raise InvalidQueryOutput("Incomplete INSERT")
    if isinstance(expression, exp.Create) and expression.expression is None:
        kind = expression.args.get("kind")
        if kind in {"VIEW", "MATERIALIZED VIEW"} or (
            kind == "TABLE"
            and not isinstance(expression.this, exp.Schema)
            and not expression.args.get("properties")
        ):
            raise InvalidQueryOutput("Incomplete CREATE")
    if db_type is not DatabaseType.POSTGRESQL and (
        isinstance(expression, exp.ILike | exp.Fetch | exp.Merge)
        or (isinstance(expression, exp.Distinct) and expression.args.get("on"))
    ):
        raise InvalidQueryOutput("Unexpected PostgreSQL syntax")
    if isinstance(expression, exp.OnConflict) and bool(expression.args.get("duplicate")) != (
        db_type is DatabaseType.MYSQL
    ):
        raise InvalidQueryOutput("Unexpected conflict clause")
    if db_type is DatabaseType.MYSQL and isinstance(expression, exp.Returning | exp.Pragma):
        raise InvalidQueryOutput("Unexpected syntax in MySQL")
    if db_type is DatabaseType.SQLITE and isinstance(
        expression, exp.Interval | exp.TruncateTable | exp.Grant | exp.Revoke
    ):
        raise InvalidQueryOutput("Unexpected syntax in SQLite")
    if db_type is DatabaseType.POSTGRESQL and isinstance(expression, exp.Pragma):
        raise InvalidQueryOutput("Unexpected syntax in PostgreSQL")


def _validate_mongo(source: bytes) -> None:
    root = Parser(_MONGO_LANGUAGE).parse(source).root_node
    statements = [
        node for node in root.named_children if node.type not in {"comment", "empty_statement"}
    ]
    if root.has_error or len(statements) != 1 or statements[0].type != "expression_statement":
        raise InvalidQueryOutput("Expected one MongoDB operation")
    node = next((node for node in statements[0].named_children if node.type != "comment"), None)
    if node is None or not _is_mongo_operation(node):
        raise InvalidQueryOutput("Expected a MongoDB shell operation rooted at db")


def _is_mongo_operation(node: Node) -> bool:
    saw_operation = False
    saw_call = False
    current: Node | None = node
    while current is not None:
        match current.type:
            case "parenthesized_expression":
                current = next(
                    (child for child in current.named_children if child.type != "comment"), None
                )
            case "call_expression":
                saw_call = True
                function = current.child_by_field_name("function")
                if function is None:
                    return False
                name = _member_name(function)
                if name in _MONGO_OPERATIONS:
                    saw_operation = True
                elif name not in _MONGO_CHAIN_METHODS:
                    return False
                current = function.child_by_field_name("object")
            case "member_expression" | "subscript_expression":
                if not saw_call or _member_name(current) is None:
                    return False
                current = current.child_by_field_name("object")
            case "identifier":
                return saw_operation and current.text == b"db"
            case _:
                return False
    return False


def _member_name(node: Node) -> bytes | None:
    if node.type == "member_expression":
        prop = node.child_by_field_name("property")
        return prop.text if prop is not None else None
    if node.type == "subscript_expression":
        index = node.child_by_field_name("index")
        if index is not None and index.type == "string" and index.text is not None:
            return index.text[1:-1]
    return None
