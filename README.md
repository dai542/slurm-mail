Slurm-Mail
==========

[![GitHub license](https://img.shields.io/github/license/neilmunday/slurm-mail)](https://github.com/neilmunday/slurm-mail/blob/main/LICENSE) [![GitHub stars](https://img.shields.io/github/stars/neilmunday/slurm-mail)](https://github.com/neilmunday/slurm-mail/stargazers) [![GitHub forks](https://img.shields.io/github/forks/neilmunday/slurm-mail)](https://github.com/neilmunday/slurm-mail/network) [![GitHub issues](https://img.shields.io/github/issues/neilmunday/slurm-mail)](https://github.com/neilmunday/slurm-mail/issues) ![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/neilmunday/slurm-mail/test_and_release.yml?label=Tests) [![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/neilmunday/slurm-mail/python-coverage-comment-action-data/endpoint.json)](https://github.com/neilmunday/slurm-mail/tree/python-coverage-comment-action-data) ![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/neilmunday/slurm-mail/pylint.yml?label=PyLint) ![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/neilmunday/slurm-mail/mypy.yml?label=mypy)

Author: Neil Munday (neil at mundayweb.com)

Repository: https://github.com/neilmunday/slurm-mail

**Contents**

1. [Introduction](#introduction)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [SMTP Settings](#smtp-settings)
6. [Customising E-mails](#customising-e-mails)
7. [Validating E-mails](#validating-e-mails)
8. [Including Job Output in E-mails](#including-job-output-in-e-mails)
9. [Job Arrays](#job-arrays)
10. [Testing](#testing)
11. [Upgrading from Slurm-Mail version 3 to 4](#upgrading-from-slurm-mail-version-3-to-4)
12. [Troubleshooting](#troubleshooting)
13. [Contributors](#contributors)

## Introduction

E-mail notifications from [Slurm](https://slurm.schedmd.com/) are rather brief and all the information is contained in the subject of the e-mail - the body is empty.

Slurm-Mail aims to address this by providing a drop in replacement for Slurm's e-mails to give users much more information about their jobs via HTML e-mails which contain the following information:

* Start/End
* Job name
* Partition
* Work dir
* Elapsed time
* Exit code
* Std out file path
* Std err file path
* No. of nodes used
* Node list
* Requested memory per node
* Maximum memory usage per node
* CPU efficiency
* Wallclock
* Wallclock accuracy

E-mails can be easily customised to your needs using the provided templates (see below).

You can also opt to include a number of lines from the end of the job's output files in the job completion e-mails (see below).

## Requirements

* cron
* logrotate
* Python 3.6 or newer
* Slurm 22 or 23
* A working e-mail server

**Note:** earlier versions of Slurm may work but are not tested with this release of Slurm-Mail.

## Installation

### RedHat and SUSE Based Operating Systems

For each release of Slurm-Mail, RPMs for RedHat 7/8/9 and SUSE 15 based operating systems are provided at [releases](https://github.com/neilmunday/slurm-mail/releases).

Once downloaded, install using your appropriate package manager, e.g. for Rocky Linux 8:

```bash
dnf localinstall ./slurm-mail-*.noarch.rpm
```

For other operating systems that use RPM packages you can create a package for your OS like so:

```bash
dnf -y install python36 rpm-build tar
git clone https://github.com/neilmunday/slurm-mail
slurm-mail/build-tools/build-rpm.sh
```

The RPM will be written to `~/rpmbuild/RPMS/noarch`.

### Ubuntu 20 and 22

Pre-built Ubuntu 20 and 22 packages are provided at [releases](https://github.com/neilmunday/slurm-mail/releases).

For other Debian variants you can create a package for your OS like so:

```bash
sudo apt-get install -y fakeroot dh-python lintian lsb-release python3 python3-stdeb
git clone https://github.com/neilmunday/slurm-mail
slurm-mail/build-tools/build-deb.sh
```

At the end of the execution the location of the built package will be written to stdout.

To install the generated package for example:

```bash
apt-get install -y cron logrotate python3 slurm-client
dpkg --force-all -i /tmp/slurm-mail_4.3-ubuntu1_all.deb
```

### From source (as root)

```bash
git clone https://github.com/neilmunday/slurm-mail
cd slurm-mail
python setup.py install
cp etc/logrotate.d/slurm-mail /etc/logrotate.d/
cp etc/cron.d/slurm-mail /etc/cron.d/
install -d -m 700 -o slurm -g slurm /var/log/slurm-mail
```

**Note:** Depending on your operating system's Python set-up, it is possible that `setuptools` might install Slurm-Mail to `/usr/local` rather than `/usr`.

## Configuration

Edit `/etc/slurm-mail/slurm-mail.conf` to suit your needs. For example, check that the location of `sacct` is correct. If you are installing from source check that the log and spool directories are set to your desired values.

Change the value of `MailProg` in your `slurm.conf` file to `/usr/bin/slurm-spool-mail`. By default the Slurm config file will be located at `/etc/slurm/slurm.conf`.

Restart `slurmctld`:

```bash
systemctl restart slurmctld
```

Slurm-Mail will now log e-mail requests from Slurm users to the Slurm-Mail spool directory `/var/spool/slurm-mail`.

The cron job created during installation at `/etc/cron.d/slurm-mail` will execute once per minute to process the spool files, thus making sure that `slurmctld` is not blocked by processing e-mails.

## SMTP Settings

By default Slurm-Mail will send e-mails to a mail server running on the same host as Slurm-Mail is installed on, i.e. `localhost`.

You can edit the `smtp` configuration options in `/etc/slurm-mail/slurm-mail.conf`. For example, to send e-mails via Gmail's SMTP server set the following settings:

```
smtpServer = smtp.gmail.com
smtpPort = 587
smtpUseTls = yes
smtpUserName = your_email@gmail.com
smtpPassword = your_gmail_password
```

> **_NOTE:_**  As this file will contain your Gmail password make sure that it has the correct owner, group and file access permissions.

If your SMTP server does not require a login, leave `smtpUserName` and `smtpPassword` set to null, i.e.

```
smtpUserName =
smtpPassword =
```

For SMTP servers that use SSL rather than starttls please set `smtpUseSsl = yes`.

## Customising E-mails

### Templates

Slurm-Mail uses Python's [string.Template](https://docs.python.org/3/library/string.html#template-strings) class to create the e-mails it sends. Under Slurm-Mail's `/etc/slurm-mail/templates` directory you will find the following files that you can edit to customise e-mails to your needs.

| Filename                  | Template Purpose                                                  |
| ------------------------- | ----------------------------------------------------------------- |
| ended-array.tpl           | Used for jobs in an array that have finished.                     |
| ended-array_summary       | Used when all jobs in an array have finished.                     |
| ended.tpl                 | Used for jobs that have finished.                                 |
| invalid-dependency.tpl    | Used when a job has an invalid dependency.                        |
| job-table.tpl             | Used to create the job info table in e-mails.                     |
| never-ran.tpl             | Used for jobs that never ran.                                     |
| signature.tpl             | Used to create the e-mail signature.                              |
| staged-out.tpl            | Used when a job's burst buffer stage has completed.               |
| started.tpl               | Used for jobs that have started.                                  |
| started-array-summary.tpl | Used when the first job in an array has started.                  |
| started-array.tpl         | Used for the first job in an array that has started.              |
| time.tpl                  | Used when a job reaches a percentage of it's time limit.          |

Each template has a number of variables which can be used in the generation of e-mails. Please see [TEMPLATES](TEMPLATES.md) for futher details.

### Styling

You can adjust the font style, size, colours etc. by editing the Cascading Style Sheet (CSS) file `/etc/slurm-mail/style.css` used for generating the e-mails.

### Date/time format

To change the date/time format used for job start and end times in the e-mails, change the `datetimeFormat` configuration option in `/etc/slurm-mail/slurm-mail.conf`. The format string used is the same as Python's [datetime.strftime function](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior).

### E-mail subject

To change the subject of the e-mails, change the `emailSubject` configuration option in `/etc/slurm-mail`. You use the following place holders in the string:

| Place holder | Value                   |
| ------------ | ----------------------- |
| $CLUSTER     | The name of the cluster |
| $JOB_NAME    | The name of the job     |
| $JOB_ID      | The Slurm ID of the job |
| $STATE       | The state of the job    |

## Validating E-mails

By default Slurm-Mail will not perform any checks on the destination e-mail address (i.e the value supplied to `sbatch` via `--mail-user`). If you would like Slurm-Mail to only send e-mails for jobs that correspond to a valid e-mail address (e.g. user@some.domain) then you can set the `validateEmail` option in `/etc/slurm-mail/slurm-mail.conf` to `true`. E-mail addresses that failed this check will be logged in `/var/log/slurm-mail/slurm-send-mail.log` as an error.

The regular expression used to validate e-mail addresses can be configured by adjusting the `emailRegEx` value in `/etc/slurm-mail/slurm-mail.conf`.

## Including Job Output in E-mails

In `/etc/slurm-mail/slurm-mail.conf` you can set the `includeOutputLines` to the number of lines to include from the end of each job's standard out and standard error files.

Notes:

* if the user has decided to use the same file for both standard output and standard error then there will be only one section of job output in the job completion e-mails.
* Job output can only be included if the process that is running `slurm-send-mail.py` is able to read the user's output files.
* Due to the way `scontrol` reports filenames that use Slurm's [filename patterns](https://slurm.schedmd.com/sbatch.html#SECTION_%3CB%3Efilename-pattern%3C/B%3E) only these patterns are supported when including job output in e-mails: `%A`, `%a`, `%j`, `%u`, and `%x`.

## Job Arrays

Slurm-Mail will honour the behaviour of `--mail-type` option of `sbatch` for job arrays. If a user specifies `--mail-type=ARRAY_TASKS` then Slurm-Mail will send notification e-mails for all jobs in the array. If you want to limit the number of e-mails that will be sent in this scenario then change the `arrayMaxNotifications` parameter in `slurm-mail.conf` to a value greater than zero.

# Development

Clone this repository to your desktop and make sure you have a supported version of Python installed (see *Requirements* above).

Pull requests are welcome!

A VSCode settings file is provided in this repository and is configured to allow you to run unit tests from the GUI.

# Testing

In order to run the unit tests you will need to install `pylint`, e.g.

```bash
pip3 install --user pylint
```

The unit tests can be found at [tests/unit](tests/unit) and can be invoked from either VSCode or from the command line, e.g.

```bash
pylint setup.py src/slurmmail/*.py tests/unit/*.py tests/integration/docker-slurm/*.py tests/integration/*.py
```

Integration tests can be found at [tests/integration](tests/integration) which also contains a Docker compose file which allows you to experiment with a demo of Slurm-Mail complete with [MailHog](https://hub.docker.com/r/mailhog/mailhog/) as a working mail server and webmail client.

## Upgrading from Slurm-Mail version 3 to 4

Version 4.0 onwards **no longer installs** to the `/opt/slurm-mail`. Instead from version 4.0 onwards install using Python's `setuptools` module. If your current Slurm-Mail 3.x installation was installed by your operating system's package manager, then you can just upgrade your installation using your package manager (e.g. `yum`, `dnf`).

If not, then proceed as follows:

1. install Slurm-Mail 4 using one of the methods describe above - take note of where the scripts and config files are installed (e.g. `/usr/bin` and `/etc`).

2. If you **have not** modified any template files you can skip this step.

```bash
cp /opt/slurm-mail/conf.d/templates/* /etc/slurm-mail/templates/
```

3. If you **have not** modified Slurm-Mail's `style.css` file you can skip this step.

```bash
cp /opt/slurm-mail/conf.d/style.css /etc/slurm-mail/
```

4. If you **have not** modified `slurm-mail.conf` you can skip this step.

```
cp /opt/slurm-mail/conf.d/slurm-mail.conf /etc/slurm-mail/
```

5. Update your Slurm installation's `slurm.conf` file:

```
MailProg=/usr/bin/slurm-spool-mail
```

Now restart `slurmctld`:

```bash
systemctl restart slurmctld
```

6. Edit `/etc/cron.d/slurm-mail` and set the path of the executable to: `/usr/bin/slurm-send-mail`

7. If you are sure you will no longer need the old version:

```
rm -rf /opt/slurm-mail
```

## Troubleshooting

1. Check that spool files are being created under: `/var/spool/slurm-mail`. If they are not:

* check `cron` is working
* check for invocation of `/usr/bin/slurm-spool-mail` in the `slurmctld` logs

2. If spool files are being created but not purged please comment out `logFile` in the `[slurm-send-mail]` section in `/etc/slurm-mail/slurm-mail.conf` and run (as root): `/usr/bin/slurm-send-mail -v` at the console.

3. If `/usr/bin/slurm-send-mail` is executing ok but you are not receiving e-mails, then check the mail logs on your server for any mail delivery errors.

## Contributors

Thank you to the following people who have contributed code improvements, features and aided the development of Slurm-Mail:

* [Dan Barker (@danbarke)](https://www.github.com/danbarke)
* [David Murray (@dajamu)](https://www.github.com/dajamu)
* [drhey (@drhey)](https://www.github.com/drhey)
* [hakasapl (@hakasapl)](https://www.github.com/hakasapl)
* [Jan-Christoph Klie (@jcklie)](https://github.com/jcklie)
* [langefa (@langefa)](https://github.com/langefa)
* [rzegson (@rzegson)](https://github.com/rzegson)
* [Mehran Khodabandeh (@mkhodabandeh)](https://www.github.com/mkhodabandeh)
* [Neil Prockter (@mrgum)](https://github.com/mrgum)
* [sdx23 (@sdx23)](https://www.github.com/sdx23)
* [Simon Feltman (@sfeltman)](https://www.github.com/sfeltman)
* [Woody Chang (@jitkang)](https://github.com/jitkang)
