import logging
import os

from roveranalyzer.dockerrunner.dockerrunner import (
    DockerCleanup,
    DockerReuse,
    DockerRunner,
)


class VadereRunner(DockerRunner):
    class LogLevel:
        OFF = "OFF"
        FATAL = "FATAL"
        ERROR = "ERROR"
        WARN = "WARN"
        INFO = "INFO"
        DEBUG = "DEBUG"
        TRACE = "TRACE"
        ALL = "ALL"

    def __init__(
        self,
        image="sam-dev.cs.hm.edu:5023/rover/crownet/vadere",
        tag="latest",
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
        traci_port=9998,
        loglevel=LogLevel.DEBUG,
        logfile=os.devnull,
        show_gui=False,
        run_args_override=None,
    ):
        """
        start Vadere server waiting for exactly ONE connection on given traci_port. After
        simulation returns the container will stop.
        """

        cmd = [
            "java",
            "-jar",
            "/opt/vadere/vadere/VadereManager/target/vadere-server.jar",
            "--loglevel",
            loglevel,
            "--logname",
            logfile,
            "--port",
            str(traci_port),
            "--bind",
            "0.0.0.0",
            "--single-client",
        ]
        if show_gui:
            cmd.append("--gui-mode")

        logging.debug(f"exec_single_server cmd: {cmd}")
        if run_args_override is None:
            run_args_override = {}

        return self.run(cmd, **run_args_override)

    def exec_start_vadere_laucher(self):
        """
        start the vadere-laucher.py script in the container which creates multiple Vadere
        instances inside ONE container.
        """
        pass

    def exec_vadere_gui(self):
        """
        start vadere gui to create or execute vadere scenarios.
        """
        pass