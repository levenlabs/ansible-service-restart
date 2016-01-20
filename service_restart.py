#!/usr/bin/python

DOCUMENTATION = '''
---
module: service_restart
author:
    - "Leven Labs"
short_description: Actually restart systemd services.
description:
    - Instead of stop/start, service_restart will actually just restart the
    systemd service.
options:
    name:
        required: true
        description:
        - Name of the service.
    arguments:
        description:
        - Additional arguments provided on the command line
        aliases: [ 'args' ]
'''

EXAMPLES = '''
# Example action to restart nginx
- service_restart: name=nginx
'''

import os
import select

# from ansible/ansible-modules-core system/service.py
def execute_command(module, cmd, daemonize=False):

    # Most things don't need to be daemonized
    if not daemonize:
        return module.run_command(cmd)

    # This is complex because daemonization is hard for people.
    # What we do is daemonize a part of this module, the daemon runs the
    # command, picks up the return code and output, and returns it to the
    # main process.
    pipe = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(pipe[0])
        # Set stdin/stdout/stderr to /dev/null
        fd = os.open(os.devnull, os.O_RDWR)
        if fd != 0:
            os.dup2(fd, 0)
        if fd != 1:
            os.dup2(fd, 1)
        if fd != 2:
            os.dup2(fd, 2)
        if fd not in (0, 1, 2):
            os.close(fd)

        # Make us a daemon. Yes, that's all it takes.
        pid = os.fork()
        if pid > 0:
            os._exit(0)
        os.setsid()
        os.chdir("/")
        pid = os.fork()
        if pid > 0:
            os._exit(0)

        # Start the command
        if isinstance(cmd, basestring):
            cmd = shlex.split(cmd)
        p = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=lambda: os.close(pipe[1]))
        stdout = ""
        stderr = ""
        fds = [p.stdout, p.stderr]
        # Wait for all output, or until the main process is dead and its output is done.
        while fds:
            rfd, wfd, efd = select.select(fds, [], fds, 1)
            if not (rfd + wfd + efd) and p.poll() is not None:
                break
            if p.stdout in rfd:
                dat = os.read(p.stdout.fileno(), 4096)
                if not dat:
                    fds.remove(p.stdout)
                stdout += dat
            if p.stderr in rfd:
                dat = os.read(p.stderr.fileno(), 4096)
                if not dat:
                    fds.remove(p.stderr)
                stderr += dat
        p.wait()
        # Return a JSON blob to parent
        os.write(pipe[1], json.dumps([p.returncode, stdout, stderr]))
        os.close(pipe[1])
        os._exit(0)
    elif pid == -1:
        module.fail_json(msg="unable to fork")
    else:
        os.close(pipe[1])
        os.waitpid(pid, 0)
        # Wait for data from daemon process and process it.
        data = ""
        while True:
            rfd, wfd, efd = select.select([pipe[0]], [], [pipe[0]])
            if pipe[0] in rfd:
                dat = os.read(pipe[0], 4096)
                if not dat:
                    break
                data += dat
        return json.loads(data)


def main():
    module = AnsibleModule(
        argument_spec = dict(
            name = dict(required=True),
            arguments = dict(aliases=['args'], default=''),
        ),
        supports_check_mode=True
    )

    name = module.params.get('name')

    if module.check_mode:
        module.exit_json(changed=True, msg='restarting service')

    action = 'restart'
    addl_arguments = module.params.get('arguments', '')
    cmd = "systemctl %s %s %s" % (action, name, addl_arguments)

    (rc, out, err) = execute_command(module, cmd, daemonize=True)

    if rc != 0:
        if err:
            module.fail_json(msg=err)
        else:
            module.fail_json(msg=out)

    result = {}
    result['name'] = name
    result['changed'] = True

    module.exit_json(**result)

from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
