import pytest

from app.sql_guard import SQLGuardError, validate_read_only_sql


def test_allows_select_from_approved_table() -> None:
    query = validate_read_only_sql(
        "SELECT NAME, MARKS FROM STUDENT WHERE MARKS > 90",
        allowed_tables=["STUDENT"],
    )
    assert "SELECT" in query.upper()
    assert "STUDENT" in query.upper()


def test_allows_select_without_a_table() -> None:
    assert "SELECT" in validate_read_only_sql("SELECT 1", allowed_tables=[]).upper()


@pytest.mark.parametrize(
    "query",
    [
        "DELETE FROM STUDENT",
        "DROP TABLE STUDENT",
        "UPDATE STUDENT SET MARKS = 0",
        "SELECT * FROM STUDENT; DELETE FROM STUDENT",
    ],
)
def test_rejects_unsafe_sql(query: str) -> None:
    with pytest.raises(SQLGuardError):
        validate_read_only_sql(query, allowed_tables=["STUDENT"])


def test_rejects_unknown_table() -> None:
    with pytest.raises(SQLGuardError, match="not allowed"):
        validate_read_only_sql("SELECT * FROM PAYMENTS", allowed_tables=["STUDENT"])

