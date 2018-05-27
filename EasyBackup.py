from lark import Lark
import abc
import os
import shutil
import datetime
import time
from daemon import Daemon
import argparse
import logger

log = logger.logger()

text = """
backup parser.py to lol.py
backup parser.py to lol.py : every 3 hours
backup parser.py to lol.py : every 5 minutes
backup parser.py to lol.py : every 5 hours
backup parser.py to lol3.py : at 17 : 22
"""

test = """
backup parser.py to lol.py : every 2 minutes
"""


class BackupTask(metaclass=abc.ABCMeta):

    def backup_file(self):
        self._run_backup()

    @abc.abstractmethod
    def _run_backup(self):
        raise NotImplementedError()


class DirectBackupTask(BackupTask):

    def __init__(self, source, destination):
        self._source = source
        self._destination = destination

    def _run_backup(self):
        if os.path.exists(self._source):
            log.info("Backuping {} to {}".format(self._source, self._destination))
            if os.path.isdir(self._source):
                log.debug("{} is a directory".format(self._source))
                if os.path.exists(self._destination):
                    log.debug("{} destination ({}) exists removing".format(self._source, self._destination))
                    shutil.rmtree(self._destination)
                    log.debug("Destination {} removed".format(self._destination))
                log.debug("Copying {} directory to {}".format(self._source, self._destination))
                shutil.copytree(self._source, self._destination)
                log.debug("Copy of {} to {} done".format(self._source, self._destination))
            else:
                log.debug("Copying {} file to {}".format(self._source, self._destination))
                shutil.copy2(self._source, self._destination)
                log.debug("Copy of {} to {} done".format(self._source, self._destination))
        else:
            log.error("Cannot backup {} to {} because source does not exist".format(self._source, self._destination))


class TimeConditionedBackup(BackupTask):

    def __init__(self, source, destination, time_condition_lambda):
        assert callable(time_condition_lambda)

        self._creation_date = datetime.datetime.now()
        self._backup_task = DirectBackupTask(source, destination)
        self._time_condition = time_condition_lambda

    def _run_backup(self):
        if self._time_condition(self._creation_date):
            self._backup_task.backup_file()


def every_minutes(nb_minutes):
    def condition_function(begin_dt):
        assert isinstance(begin_dt, datetime.datetime)

        now = datetime.datetime.now()
        delta = now - begin_dt
        elapsed_minutes = int(delta.total_seconds() / 60)

        return elapsed_minutes % nb_minutes == 0
    return condition_function


def specific_time(hour, minute):
    def condition_function(begin_dt):
        assert isinstance(begin_dt, datetime.datetime)

        now = datetime.datetime.now()

        return now.hour == hour and now.minute == minute
    return condition_function


class AppDaemon(Daemon):

    def __init__(self, program_file_path, pidfile="run.pid"):
        super().__init__(pidfile)
        self._program_file_path = program_file_path

    def run(self):
        app = App(self._program_file_path)
        app.run()


class App:

    def __init__(self, program_file_path):

        assert os.path.isfile(program_file_path)

        self._program = open(program_file_path).read()
        self._conditional_backups = list()

        self._parse_run()

    def run(self):
        if len(self._conditional_backups) > 0:
            while True:
                for backup_task in self._conditional_backups:
                    backup_task.backup_file()
                log.info("Sleeping for a minute")
                time.sleep(60)

    def _parse_run(self):
        grammar = open("backup_dsl.ebnf").read()
        parser = Lark(grammar)
        tree = parser.parse(self._program)

        for inst in tree.children:
            source = inst.children[0].strip()
            destination = inst.children[1].strip()

            if len(inst.children) == 2:
                backup_task = DirectBackupTask(source, destination)
                log.info("Running backup task")
                backup_task.backup_file()
            else:
                time_type_data = inst.children[2]
                log.info("Registering backup task with time condition")
                if time_type_data.data == "avg_time_expresion":
                    time_data = time_type_data.children[0]
                    if time_data.data == "every_nb_minutes":
                        nb_minutes = int(time_data.children[0].value)
                        backup_task = TimeConditionedBackup(source, destination, every_minutes(nb_minutes))
                        self._conditional_backups.append(backup_task)
                    elif time_data.data == "every_nb_hours":
                        nb_hours = int(time_data.children[0].value)
                        backup_task = TimeConditionedBackup(source, destination, every_minutes(nb_hours * 60))
                        self._conditional_backups.append(backup_task)
                    elif time_data.data == "every_hour":
                        backup_task = TimeConditionedBackup(source, destination, every_minutes(60))
                        self._conditional_backups.append(backup_task)
                    elif time_data.data == "every_minute":
                        backup_task = TimeConditionedBackup(source, destination, every_minutes(1))
                        self._conditional_backups.append(backup_task)
                elif time_type_data.data == "precise_time_expression":
                    time_data_hour = int(time_type_data.children[0].value)
                    time_data_minute = int(time_type_data.children[1].value)
                    backup_task = TimeConditionedBackup(source, destination, specific_time(time_data_hour, time_data_minute))
                    self._conditional_backups.append(backup_task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Backup program file", required=True)
    parser.add_argument("-d", "--daemonize", help="Makes this run as a daemon",
                        action="store_true")
    parser.add_argument("--stop", help="With -d makes this run as a daemon",
                        action="store_true")
    parser.add_argument("--restart", help="With -d stops the daemon",
                        action="store_true")
    arguments = parser.parse_args()

    if arguments.daemonize:
        daemon = AppDaemon(arguments.file)

        if not arguments.stop and not arguments.restart:
            log.info("Starting daemon")
            daemon.start()
        elif arguments.stop:
            log.info("Stopping daemon")
            daemon.stop()
        elif arguments.restart:
            log.info("Restarting daemon")
            daemon.restart()

    else:
        app = App(arguments.file)
        app.run()
