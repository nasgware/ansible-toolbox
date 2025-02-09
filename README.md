# ansible-toolbox

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ansible_toolbox)

## What is this?

Simple ansible-playbook runner to execute playbooks in a (docker) container, easy to use, promoting isolation, portability, reproducibility, optimal to integrate in CI/CD pipelines.

## Why?

Managing multiple versions of Ansible, Python, and their dependencies can be complex and challenging, potentially causing conflicts and clutter in the orchestrator environment. The ansible-toolbox offers an efficient solution by allowing you to encapsulate these environments within a container, thereby maintaining a clean and organized system.

## Features
- Lightweight
- Zero dependencies (uses only Python's standard library)
- Compatible with Python 3.9 to 3.13

## How to use?

:warning: **Warning:** make sure you have `docker` somwhere in the `$PATH`.

Now that you have everything in place, issue the following command,

Go to your favourite terminal and install the package, using the following command,

```console
$ pip install --user ansible_toolbox # what works for you, based on your specific scenario
```

After you have installed ansible-toolbox, jump back the terminal, and create a simple test playbook,

```yaml
# Filename: playbook.yaml
---
- hosts: localhost
  gather_facts: false
  tasks:
  - name: This is a task
    debug: 
      msg: "this is a test"
```

Now that you have everything in place, issue the following command,

⚠️ `at` is yet another linux command, so if you actually use `at` you may get in trouble.

```console
$ at ansible-playbook playbook.yaml
Ansible Toolbox Docker image not found. Building...
Building Docker image ansible-toolbox:latest...
[+] Building 45.4s (6/6) FINISHED                                                                                                                                                                                                                           docker:default
 => [internal] load build definition from tmp1afvirv_.dockerfile                                                                                                                                                                                                      0.2s
 => => transferring dockerfile: 555B                                                                                                                                                                                                                                  0.0s
 => [internal] load metadata for docker.io/library/alpine:latest                                                                                                                                                                                                      1.3s
 => [internal] load .dockerignore                                                                                                                                                                                                                                     0.2s
 => => transferring context: 2B                                                                                                                                                                                                                                       0.0s
 => [1/2] FROM docker.io/library/alpine:latest@sha256:56fa17d2a7e7f168a043a2712e63aed1f8543aeafdcee47c58dcffe38ed51099                                                                                                                                                1.0s
 => => resolve docker.io/library/alpine:latest@sha256:56fa17d2a7e7f168a043a2712e63aed1f8543aeafdcee47c58dcffe38ed51099                                                                                                                                                0.1s
 => => sha256:56fa17d2a7e7f168a043a2712e63aed1f8543aeafdcee47c58dcffe38ed51099 9.22kB / 9.22kB                                                                                                                                                                        0.0s
 => => sha256:483f502c0e6aff6d80a807f25d3f88afa40439c29fdd2d21a0912e0f42db842a 1.02kB / 1.02kB                                                                                                                                                                        0.0s
 => => sha256:b0c9d60fc5e3fa2319a86ccc1cdf34c94c7e69766e8cebfb4111f7e54f39e8ff 581B / 581B                                                                                                                                                                            0.0s
 => => sha256:1f3e46996e2966e4faa5846e56e76e3748b7315e2ded61476c24403d592134f0 3.64MB / 3.64MB                                                                                                                                                                        0.5s
 => => extracting sha256:1f3e46996e2966e4faa5846e56e76e3748b7315e2ded61476c24403d592134f0                                                                                                                                                                             0.1s
 => [2/2] RUN apk add --no-cache     ca-certificates     openssh     git     python3     py3-pip     && python3 -m venv /install/.venv     && pip install --no-cache-dir ansible requests==2.32.3 docker==7.1.0      && rm -rf /tmp/* /var/cache/apk/* /root/.cache  39.0s
 => exporting to image                                                                                                                                                                                                                                                3.3s 
 => => exporting layers                                                                                                                                                                                                                                               3.2s 
 => => writing image sha256:b10d2705991429f15523c7ec20f70ee37f7d206bace72db54288832464262f07                                                                                                                                                                          0.0s 
 => => naming to docker.io/library/ansible-toolbox:latest                                                                                                                                                                                                             0.0s 
Docker image built successfully.                                                                                                                                                                                                                                           
Executing Docker command: /usr/bin/docker run --rm --name ansible-toolbox --network host --user 1000:1000 --cap-drop NET_BIND_SERVICE --cap-drop SETUID --cap-drop SETGID --security-opt no-new-privileges -v /etc/passwd:/etc/passwd:ro,z -v /etc/group:/etc/group:ro,z -v /tmp:/tmp:z -v /var/tmp:/var/tmp:z -v /home/user/ansible-toolbox:/workspace:ro,z -e HOME=/tmp -e TERM=xterm-256color -e ANSIBLE_LOCAL_TEMP=/tmp -e ANSIBLE_REMOTE_TEMP=/tmp/$(whoami) -e ANSIBLE_STDOUT_CALLBACK=debug -e ANSIBLE_CONFIG=/workspace/ansible.cfg -e ANSIBLE_FORCE_COLOR=1 ansible-toolbox:latest /bin/sh -c cd /workspace && ansible-playbook /workspace/playbook.yaml
[WARNING]: No inventory was parsed, only implicit localhost is available
[WARNING]: provided hosts list is empty, only localhost is available. Note that
the implicit localhost does not match 'all'

PLAY [localhost] ***************************************************************

TASK [This is a task] **********************************************************
ok: [localhost] => {}

MSG:

this is a test

PLAY RECAP *********************************************************************
localhost                  : ok=1    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   
```

That's all, that's the basics. Addicionally you can use the following options to fit 
with your use case,

| Flag/Option           | Description                                                              |
| --------------------- | ------------------------------------------------------------------------ |
| `--at-help`           | Show this help message and exit.                                         |
| `command`             | The Ansible command to run. This can be any valid Ansible CLI command.   |
| `--at-i`              | Run in interactive mode.                                                 |
| `--at-add-py-package` | Add additional Python packages to the toolbox. Multiple entries allowed. |
| `--at-volume`         | Add additional volumes to mount. Multiple entries allowed.               |
| `--at-env`            | Add additional environment variables. Multiple entries allowed.          |

## TODO
- [ ] Support for remote docker engines
- [ ] Custom dockerfiles
- [ ] Support for ansible-galaxy dependencies
- [ ] Support for diferent images
- [ ] Diff images, when content of the newly created image changes
- [ ] Support for podman

## Contributing

Feel free to fork and open pull requests.
