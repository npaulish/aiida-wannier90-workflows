# pylint: disable=redefined-outer-name
"""Tests for the ``Wannier90OpenGridWorkChain.get_builder_from_protocol`` method."""
import pytest

from aiida.engine import ProcessBuilder
from aiida.plugins import WorkflowFactory

from aiida_quantumespresso.common.types import ElectronicType, SpinType

from aiida_wannier90_workflows.common.types import WannierProjectionType

Wannier90OpenGridWorkChain = WorkflowFactory("wannier90_workflows.open_grid")


def test_get_available_protocols():
    """Test ``Wannier90OpenGridWorkChain.get_available_protocols``."""
    protocols = Wannier90OpenGridWorkChain.get_available_protocols()
    assert sorted(protocols.keys()) == ["fast", "moderate", "precise"]
    assert all("description" in protocol for protocol in protocols.values())


def test_get_default_protocol():
    """Test ``Wannier90OpenGridWorkChain.get_default_protocol``."""
    assert Wannier90OpenGridWorkChain.get_default_protocol() == "moderate"


@pytest.mark.parametrize("structure", ("Si", "H2O", "GaAs", "BaTiO3"))
def test_scdm(generate_builder_inputs, data_regression, serialize_builder, structure):
    """Test ``Wannier90OpenGridWorkChain.get_builder_from_protocol`` for the default protocol."""

    inputs = generate_builder_inputs(structure)
    builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
        **inputs, print_summary=False
    )

    assert isinstance(builder, ProcessBuilder)
    data_regression.check(serialize_builder(builder))


@pytest.mark.parametrize("structure", ("Si", "H2O", "GaAs", "BaTiO3"))
def test_atomic_projectors_qe(
    generate_builder_inputs, data_regression, serialize_builder, structure
):
    """Test ``Wannier90OpenGridWorkChain.get_builder_from_protocol`` for the default protocol."""

    inputs = generate_builder_inputs(structure)
    builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
        **inputs,
        projection_type=WannierProjectionType.ATOMIC_PROJECTORS_QE,
        print_summary=False,
    )

    assert isinstance(builder, ProcessBuilder)
    data_regression.check(serialize_builder(builder))


def test_electronic_type(generate_builder_inputs):
    """Test ``Wannier90OpenGridWorkChain.get_builder_from_protocol`` with ``electronic_type`` keyword."""
    with pytest.raises(NotImplementedError):
        builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
            **generate_builder_inputs(),
            electronic_type=ElectronicType.AUTOMATIC,
            print_summary=False,
        )

    builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
        **generate_builder_inputs(),
        electronic_type=ElectronicType.INSULATOR,
        open_grid_only_scf=False,
        print_summary=False,
    )
    for namespace, occupations in zip((builder.scf, builder.nscf), ("fixed", "fixed")):
        parameters = namespace["pw"]["parameters"].get_dict()
        assert parameters["SYSTEM"]["occupations"] == occupations
        assert "degauss" not in parameters["SYSTEM"]
        assert "smearing" not in parameters["SYSTEM"]

    builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
        **generate_builder_inputs(),
        electronic_type=ElectronicType.METAL,
        open_grid_only_scf=False,
        print_summary=False,
    )
    for namespace, occupations in zip(
        (builder.scf, builder.nscf), ("smearing", "smearing")
    ):
        parameters = namespace["pw"]["parameters"].get_dict()
        assert parameters["SYSTEM"]["occupations"] == occupations
        assert "degauss" in parameters["SYSTEM"]
        assert "smearing" in parameters["SYSTEM"]


def test_spin_type(generate_builder_inputs):
    """Test ``Wannier90OpenGridWorkChain.get_builder_from_protocol`` with ``spin_type`` keyword."""
    # with pytest.raises(NotImplementedError):
    #     for spin_type in [SpinType.COLLINEAR, SpinType.NON_COLLINEAR]:
    #         builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
    #             **generate_builder_inputs(), spin_type=spin_type, print_summary=False
    #         )
    # TODO: add tests for collinear and noncollinears

    builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
        **generate_builder_inputs(),
        spin_type=SpinType.NONE,
        open_grid_only_scf=False,
        print_summary=False,
    )
    for namespace in [builder.scf, builder.nscf]:
        parameters = namespace["pw"]["parameters"].get_dict()
        assert "nspin" not in parameters["SYSTEM"]
        assert "starting_magnetization" not in parameters["SYSTEM"]


def test_projection_type(generate_builder_inputs):
    """Test ``Wannier90OpenGridWorkChain.get_builder_from_protocol`` with ``projection_type`` keyword."""
    # with pytest.raises(NotImplementedError):
    #     for projection_type in [
    #         WannierProjectionType.ANALYTIC, WannierProjectionType.RANDOM,
    #         WannierProjectionType.ATOMIC_PROJECTORS_EXTERNAL
    #     ]:
    #         builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
    #             **generate_builder_inputs(), projection_type=projection_type
    #         )

    builder = Wannier90OpenGridWorkChain.get_builder_from_protocol(
        **generate_builder_inputs(),
        projection_type=WannierProjectionType.ATOMIC_PROJECTORS_QE,
        print_summary=False,
    )
    for namespace in [
        builder.wannier90,
    ]:
        parameters = namespace["wannier90"]["parameters"].get_dict()
        assert "auto_projections" in parameters
