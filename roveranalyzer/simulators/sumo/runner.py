import os
import warnings

from roveranalyzer.dockerrunner import DockerCfg
from roveranalyzer.dockerrunner.dockerrunner import (
    DockerCleanup,
    DockerReuse,
    DockerRunner,
)
from roveranalyzer.utils import logger, sockcheck


class SumoRunner(DockerRunner):
    def __init__(
        self,
        image=DockerCfg("sumo"),
        tag=DockerCfg.get_default_tag(DockerCfg.VAR_SUMO_TAG),
        docker_client=None,
        name="",
        cleanup_policy=DockerCleanup.REMOVE,
        reuse_policy=DockerReuse.REMOVE_STOPPED,
        detach=False,
        journal_tag="",
    ):
        super().__init__(
            image,
            tag,
            docker_client=docker_client,
            name=name,
            cleanup_policy=cleanup_policy,
            reuse_policy=reuse_policy,
            detach=detach,
            journal_tag=journal_tag,
        )

    def _apply_default_volumes(self):
        super()._apply_default_volumes()
        # add...

    def _apply_default_environment(self):
        super()._apply_default_environment()
        # add...

    def set_run_args(self, run_args=None):
        super().set_run_args()
        # add...

    def exec_single_server(
        self,
        config_path,
        traci_port=9999,
        message_log=os.devnull,
        run_args_override=None,
    ):
        """
        This function is deprecated, please use the single_launcher
        """
        warnings.warn("SumoRunner.exec_single_server is a deprecated function.")
        cmd = [
            "sumo",
            "-v",
            "--remote-port",
            str(traci_port),
            "--configuration-file",
            config_path,
            "--message-log",
            message_log,
            "--no-step-log",
            "--quit-on-end",
        ]

        if run_args_override is None:
            run_args_override = {}

        logger.debug(f"start sumo container(single server)")
        logger.debug(f"cmd: {' '.join(cmd)}")
        run_result = self.run(cmd, **run_args_override)
        self.wait_for_log(f"listening on port {traci_port}...")
        return run_result

    def single_launcher(
        self,
        traci_port=9999,
        bind="0.0.0.0",
        message_log=os.devnull,
        run_args_override=None,
    ):
        # todo: implement how opp/runner.py in line 78
        cmd = [
            "/veins_launchd",
            "-vvv",
            "--port",
            str(traci_port),
            "--bind",
            bind,
            "--logfile",
            message_log,
            "--single-run",
        ]
        if run_args_override is None:
            run_args_override = {}

        logger.debug(f"start sumo container(single server)")
        logger.debug(f"cmd: {' '.join(cmd)}")
        run_result = self.run(cmd, **run_args_override)
        # TODO replace sockcheck.check by self.wait_for_log()
        sockcheck.check(self.name, int(traci_port))
        return run_result

    def exec_start_sumo_launcher(self):
        """
        start the launcher.py script in the container which creates multiple sumo
        instances inside ONE container.
        """
        pass

    def exec_sumo_gui(self):
        """
        start sumo gui to create or execute scenarios.
        """
        pass
