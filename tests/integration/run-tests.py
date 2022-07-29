#!/usr/bin/env python3

# pylint: disable=broad-except,consider-using-f-string,invalid-name
# pylint: disable=redefined-outer-name

#
#  This file is part of Slurm-Mail.
#
#  Slurm-Mail is a drop in replacement for Slurm's e-mails to give users
#  much more information about their jobs compared to the standard Slurm
#  e-mails.
#
#   Copyright (C) 2018-2022 Neil Munday (neil@mundayweb.com)
#
#  Slurm-Mail is free software: you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the
#  Free Software Foundation, either version 3 of the License, or (at
#  your option) any later version.
#
#  Slurm-Mail is distributed in the hope that it will be useful, but
#  WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Slurm-Mail.  If not, see <http://www.gnu.org/licenses/>.
#

"""
run-tests.py

Author: Neil Munday

Script to automatically run tests for Slurm-Mail.
"""

import argparse
import configparser
import logging
import pathlib
import os
import re
import sys
import time
import yaml  # type: ignore

import slurmmail
from slurmmail.common import check_file, check_dir, die, run_command


def echo_log(log_file: pathlib.Path):
    """
    Helper function to display the contents of the given file.
    """
    if log_file.is_file():
        with open(log_file, mode="r", encoding="utf-8") as f:
            log_output = f.read().split("\n")
            lines = ""
            for line in log_output:
                lines += "---> {0}\n".format(line)
            logging.error("%s contents:\n%s", log_file, lines)
    else:
        logging.warning("%s does not exist", log_file)


def remove_logs():
    """
    Delete Slurm-Mail log files
    """
    if spool_log.is_file():
        logging.debug("deleting: %s", spool_log)
        os.unlink(spool_log)
    else:
        logging.debug("%s does not exist", spool_log)
    if send_log.is_file():
        logging.debug("deleting: %s", send_log)
        os.unlink(send_log)
    else:
        logging.debug("deleting %s does not exist", send_log)


def wait_for_job():
    """
    Wait for all jobs to complete.
    """
    i = 0
    limit = 120
    for i in range(0, limit):
        rtn, stdout, _ = run_command("squeue --noheader")
        if rtn != 0:
            die("failed to run squeue")
        if stdout != "":
            logging.debug("waiting for jobs to finish")
            time.sleep(1)
        else:
            break
    if i == limit:
        die("jobs still running after {0}s".format(limit))


if __name__ == "__main__":

    SLURM_SEND_MAIL_EXE = pathlib.Path("/usr/bin/slurm-send-mail")
    MAIL_LOG = pathlib.Path("/var/log/supervisor/mailserver.log")
    SLURMCTLD_LOG = pathlib.Path("/var/log/slurm/slurmctld.log")

    parser = argparse.ArgumentParser(
        description="Perform tests of Slurm-Mail", add_help=True
    )
    parser.add_argument(
        "-i", "--input", help="Test input file (YAML)",
        dest="input", required=True,
    )
    parser.add_argument(
        "-o", "--output", help="Output directory", dest="output",
        required=True
    )
    parser.add_argument(
        "-t", "--test", help="Run a particular test", dest="test"
    )
    parser.add_argument(
        "-v", "--verbose", help="Turn on debug messages", dest="verbose",
        action="store_true"
    )
    args = parser.parse_args()

    log_date = "%Y/%m/%d %H:%M:%S"
    log_format = "%(asctime)s:%(levelname)s: %(message)s"
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG

    logging.basicConfig(
        format=log_format, datefmt=log_date, level=log_level
    )

    input_file = pathlib.Path(args.input)
    output_dir = pathlib.Path(args.output)
    spool_dir = pathlib.Path("/var/spool/slurm-mail")

    logging.info("using tests defined in: %s", input_file)

    check_file(SLURM_SEND_MAIL_EXE)
    check_file(input_file)
    check_dir(output_dir)
    check_dir(spool_dir)
    check_file(slurmmail.conf_file)

    spool_log = None
    send_log = None

    try:
        config = configparser.RawConfigParser()
        config.read(str(slurmmail.conf_file))
        send_log = pathlib.Path(config.get("slurm-send-mail", "logFile"))
        spool_log = pathlib.Path(config.get("slurm-spool-mail", "logFile"))
    except Exception as e:
        die("Error: {0}".format(e))

    with open(input_file, mode="r", encoding="utf-8") as stream:
        dictionary = yaml.safe_load(stream)

    if "tests" not in dictionary:
        die("invalid YAML: could not find \"tests\" definition")

    # check that slurm is up
    logging.info("waiting for Slurm...")
    slurm_ok = False
    for i in range(0, 30):
        rtn, _, _ = run_command("sinfo")
        if rtn == 0:
            slurm_ok = True
            break
        time.sleep(1)

    if not slurm_ok:
        die("no response from Slurm")
    logging.info("Slurm is ready")

    error_re = re.compile(r":ERROR:")
    passed = 0
    total = 0

    for test, fields in dictionary["tests"].items():
        if args.test and args.test != test:
            logging.info("skipping test: %s", test)
            continue
        total += 1
        logging.info("running: %s: %s", test, fields["description"])
        logging.info("creating JCF...")
        jcf_path = output_dir / "{0}.jcf".format(test)
        with open(jcf_path, mode="w", encoding="utf-8") as jcf_file:
            jcf_file.write("#!/bin/bash\n")
            jcf_file.write("#SBATCH -J {0}\n".format(test))
            jcf_file.write("#SBATCH -o {0}/%j.out\n".format(output_dir))
            if "options" in fields:
                for sbatch_option, sbatch_value in fields["options"].items():
                    jcf_file.write(
                        "#SBATCH --{0}={1}\n".format(
                            sbatch_option,
                            sbatch_value
                        )
                    )
            jcf_file.write(fields["commands"])
        # display generated JCF
        with open(jcf_path, mode="r", encoding="utf-8") as jcf_file:
            logging.debug("\n%s", jcf_file.read())
        logging.info("submitting job...")
        rtn, stdout, stderr = run_command("sbatch {0}".format(jcf_path))
        if rtn != 0:
            logging.error(
                "%s failed: could not submit job\nstdout:\n%s\nstderr:\n%s",
                test,
                stdout,
                stderr
            )
            dictionary["tests"][test]["pass"] = False
            continue
        logging.info("waiting for job to finish...")
        wait_for_job()
        # Although the job has finished there is a chance
        # that slurmctld hasn't triggered slurm-spool-mail
        # just yet.
        logging.info(
            "waiting for %s spool files...",
            fields["spool_file_total"]
        )
        spoolOk = False
        WAIT_FOR = 25
        for i in range(0, WAIT_FOR):
            if len(list(spool_dir.glob("*.mail"))) == fields["spool_file_total"]:  # noqa
                spoolOk = True
                break
            time.sleep(1)
        if spoolOk:
            logging.info("%s: spool files created ok", test)
        else:
            logging.error(
                "%s failed: no spool files after %ss", test, WAIT_FOR
            )
            dictionary["tests"][test]["pass"] = False
            if spool_log.is_file():
                echo_log(spool_log)
            if SLURMCTLD_LOG.is_file():
                echo_log(SLURMCTLD_LOG)
            remove_logs()
            continue
        rtn, stdout, stderr = run_command(str(SLURM_SEND_MAIL_EXE))
        if rtn != 0:
            logging.error(
                "failed to run %s\nsdtout:\n%s\nstderr:\n%s",
                SLURM_SEND_MAIL_EXE,
                stdout,
                stderr
            )
        if len(list(spool_dir.glob("*.mail"))) != 0:
            logging.error(
                "%s failed: spool files still present - deleting for next test",  # noqa
                test
            )
            echo_log(send_log)
            dictionary["tests"][test]["pass"] = False
            for spool_file in spool_dir.glob("*.mail"):
                logging.debug("deleting: %s", spool_file)
                os.remove(str(spool_file))
            continue
        logging.info("spool files gone, checking log files")
        if not fields["send_errors"]:
            send_log_output = None
            send_log_ok = True
            with open(send_log, mode="r", encoding="utf-8") as f:
                send_log_output = f.read().split("\n")
                for line in send_log_output:
                    match = error_re.search(line)
                    if match:
                        send_log_ok = False
                        break

            if not send_log_ok:
                lines = ""
                for line in send_log_output:
                    lines += "---> {0}\n".format(line)
                logging.error(
                    "%s failed: errors present in %s:\n%s",
                    test,
                    send_log,
                    lines
                )
                dictionary["tests"][test]["pass"] = False
                remove_logs()
                continue
        dictionary["tests"][test]["pass"] = True
        passed += 1
        logging.info("%s passed: OK", test)
        remove_logs()

    # logging.info("Mail log:")
    # echo_log(MAIL_LOG)
    # display test results
    failed = total - passed
    logging.info("passed: %d, failed: %d", passed, failed)
    if failed > 0:
        sys.exit(1)
    sys.exit(0)
