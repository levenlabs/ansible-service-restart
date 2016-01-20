# Ansible Role: service_restart

This role contains no tasks, but provides `service_restart` module.

You must include the role in a playbook or as a dependency in a role in order to
use the module.

## service_restart Module

This module will restart a service by executing `systemctl restart <name>`
instead of doing a stop/start which is what the core `service` module does.

This module was written in response to
[ansible/ansible-modules-core#1836](https://github.com/ansible/ansible-modules-core/issues/1836).

Example:

```
- name: Restart nginx
  service_restart: name=nginx
```
