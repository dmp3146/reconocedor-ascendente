import pytest

from services.analyzer_service import AnalyzerService, StageStatus


@pytest.fixture(scope="module")
def service():
    return AnalyzerService()


@pytest.mark.parametrize("source", ["10 / 0", "10 / (4 - 4)", "20 / (2 - 2)"])
def test_division_by_zero_preserves_syntax_tree_and_trace(service, source):
    stages = service.analyze_stages(source)
    assert (stages.lexical, stages.syntactic, stages.evaluation) == (
        StageStatus.CORRECT, StageStatus.ACCEPTED, StageStatus.ERROR
    )
    assert stages.error is None
    assert stages.analysis is not None
    assert stages.analysis.value is None
    assert stages.analysis.division_by_zero
    assert stages.analysis.parse_result.root is not None
    trace = stages.analysis.parse_result.trace
    assert {"shift", "reduce"} <= {step.action.kind for step in trace if step.action}
    assert trace[-1].action.kind == "accept"


@pytest.mark.parametrize(("source", "expected"), [("10 / 2", 5.0), ("0 / 5", 0.0)])
def test_successful_evaluation_has_all_stage_results(service, source, expected):
    stages = service.analyze_stages(source)
    assert (stages.lexical, stages.syntactic, stages.evaluation) == (
        StageStatus.CORRECT, StageStatus.ACCEPTED, StageStatus.CORRECT
    )
    assert stages.analysis is not None
    assert stages.analysis.value == expected


@pytest.mark.parametrize(
    ("source", "lexical", "syntactic"),
    [
        ("5 + * 3", StageStatus.CORRECT, StageStatus.ERROR),
        ("5 + @", StageStatus.ERROR, StageStatus.NOT_RUN),
    ],
)
def test_failures_identify_the_stage_and_stop_later_stages(
    service, source, lexical, syntactic
):
    stages = service.analyze_stages(source)
    assert stages.lexical == lexical
    assert stages.syntactic == syntactic
    assert stages.evaluation == StageStatus.NOT_RUN
    assert stages.analysis is None
    assert stages.error is not None
