#!/usr/bin/env python3
#!/usr/bin/python3

import sys

from tutorial.imports import *

# This is just to make sure that the systems path is set up correctly, to have correct imports, it can be ignored:

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath(".."))

run_local = True
###############################################################################################################
# Usecase: Set yourself the parameters you want to change. Do this by defining a list of dictionaries with the
# corresponding parameter. Again, the Vadere output is deleted after all scenarios run.


if __name__ == "__main__":

    output_folder = os.path.join(os.getcwd(), "first_examples_rover_01")

    ## Define the simulation to be used
    # A rover simulation is defined by an "omnetpp.ini" file and its corresponding directory.
    # Use following *.ini file:

    path2ini = os.path.join(
        os.environ["CROWNET_HOME"],
        "crownet/simulations/simple_detoure_suqc_traffic/omnetpp.ini",
    )

    ## Define parameters and sampling method
    # parameters

    parameter = [
        Parameter(
            name="number_of_agents_mean",
            simulator="dummy",
            stages=[15, 20],
        )  # number of agtens to be generated in 100s
    ]
    dependent_parameters = [
        DependentParameter(
            name="sources.[id==1].distributionParameters",
            simulator="vadere",
            equation=lambda args: [(args["number_of_agents_mean"] * 0.01 / 4)],
        ),
        DependentParameter(
            name="sources.[id==2].distributionParameters",
            simulator="vadere",
            equation=lambda args: [(args["number_of_agents_mean"] * 0.01 / 4)],
        ),
        DependentParameter(
            name="sources.[id==5].distributionParameters",
            simulator="vadere",
            equation=lambda args: [(args["number_of_agents_mean"] * 0.01 / 4)],
        ),
        DependentParameter(
            name="sources.[id==6].distributionParameters",
            simulator="vadere",
            equation=lambda args: [(args["number_of_agents_mean"] * 0.01 / 4)],
        ),
        DependentParameter(name="sim-time-limit", simulator="omnet", equation="180s"),
        DependentParameter(
            name="*.station[0].app[0].incidentTime",
            simulator="omnet",
            equation="100s",
        ),
        DependentParameter(
            name="*.radioMedium.obstacleLoss.typename",
            simulator="omnet",
            equation="DielectricObstacleLoss",
        ),
    ]

    # number of repitions for each sample
    reps = 1

    # sampling
    par_var = RoverSamplingFullFactorial(
        parameters=parameter, parameters_dependent=dependent_parameters
    ).get_sampling()

    ## Define the quantities of interest (simulation output variables)
    # Make sure that corresponding post processing methods exist in the run_script2.py file

    qoi = [
        "degree_informed_extract.txt",
        "poisson_parameter.txt",
        "time_95_informed.txt",
    ]

    # define tag of omnet and vadere docker images, see https://sam-dev.cs.hm.edu/rover/rover-main/container_registry/
    model = VadereOmnetWrapper(
        model="Coupled", vadere_tag="200527-1424", omnetpp_tag="200221-1642"
    )

    setup = CoupledDictVariation(
        ini_path=path2ini,
        config="final",
        parameter_dict_list=par_var,
        qoi=qoi,
        model=model,
        scenario_runs=reps,
        post_changes=None,
        output_path=path2tutorial,
        output_folder=output_folder,
        remove_output=True,
        seed_config=None,  # TODO ->  {"vadere": "random", "omnet": "random"},
        env_remote=None,
    )

    if os.environ["CROWNET_HOME"] is None:
        raise SystemError(
            "Please add ROVER_MAIN to your system variables to run a rover simulation."
        )

    if run_local:
        par_var, data = setup.run(1)
    else:
        par_var, data = setup.remote(-1)

    # Save results
    summary = output_folder + "_df"
    if os.path.exists(summary):
        shutil.rmtree(summary)

    os.makedirs(summary)

    par_var.to_csv(os.path.join(summary, "parameters.csv"))
    for q in qoi:
        data[q].to_csv(os.path.join(summary, f"{q}"))

    print("All simulation runs completed.")
