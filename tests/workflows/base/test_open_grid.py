"""Tests for the `OpenGridBaseWorkChain` class."""

import pytest

from aiida.common import AttributeDict
from aiida.engine import ProcessHandlerReport

from aiida_quantumespresso.calculations.open_grid import OpenGridCalculation

from aiida_wannier90_workflows.workflows.base.open_grid import OpenGridBaseWorkChain

# pylint: disable=no-member,redefined-outer-name


def test_setup(generate_workchain_open_grid_base):
    """Test `OpenGridBaseWorkChain.setup`."""
    process = generate_workchain_open_grid_base()
    process.setup()

    assert isinstance(process.ctx.inputs, AttributeDict)


@pytest.mark.parametrize(
    "npool_value",
    (
        4,
        2,
    ),
)
@pytest.mark.parametrize(
    "npool_key",
    (
        "-nk",
        "-npools",
    ),
)
def test_handle_output_stdout_incomplete(
    generate_workchain_open_grid_base,
    generate_inputs_open_grid_base,
    npool_key,
    npool_value,
):
    """Test `OpenGridBaseWorkChain.handle_output_stdout_incomplete` for restarting from OOM."""
    from aiida import orm

    inputs = {"open_grid": generate_inputs_open_grid_base()}
    # E.g. when number of MPI procs = 4, the next trial is 2
    inputs["open_grid"]["metadata"]["options"] = {
        "resources": {"num_machines": 1, "num_mpiprocs_per_machine": npool_value},
        "max_wallclock_seconds": 3600,
        "withmpi": True,
        "scheduler_stderr": "_scheduler-stderr.txt",
    }
    inputs["open_grid"]["settings"] = orm.Dict(
        dict={"cmdline": [npool_key, f"{npool_value}"]}
    )
    process = generate_workchain_open_grid_base(
        exit_code=OpenGridCalculation.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE,
        inputs=inputs,
        test_name="out_of_memory",
    )
    process.setup()

    # Direct call to the handler
    result = process.handle_output_stdout_incomplete(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == 0

    new_npool_value = npool_value // 2
    assert (
        process.ctx.inputs["metadata"]["options"]["resources"][
            "num_mpiprocs_per_machine"
        ]
        == new_npool_value
    )
    assert process.ctx.inputs["settings"]["cmdline"] == [
        npool_key,
        f"{new_npool_value}",
    ]

    # The `inspect_process` will call again the `handle_output_stdout_incomplete` because the
    # `ERROR_OUTPUT_STDOUT_INCOMPLETE` exit code is still there.
    result = process.inspect_process()
    new_npool_value = npool_value // 4
    if new_npool_value == 0:
        assert result == OpenGridBaseWorkChain.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE
        new_npool_value = 1
    else:
        assert result.status == 0
    assert (
        process.ctx.inputs["metadata"]["options"]["resources"][
            "num_mpiprocs_per_machine"
        ]
        == new_npool_value
    )
    assert process.ctx.inputs["settings"]["cmdline"] == [
        npool_key,
        f"{new_npool_value}",
    ]
