# Command runner network diagnosis

2026-11-10. Read-only diagnostics in the active Codex command sandbox. No macOS DNS,
Tailscale, firewall or Codex permission settings were changed.

The active session explicitly has restricted command networking. Observations:

| Probe | Result |
|---|---|
| Resolve localhost | Returns loopback addresses |
| Resolve github.com / api.github.com | `getaddrinfo` fails |
| Resolve configured Mac Studio Tailscale hostname | `getaddrinfo` fails |
| scutil --dns | No DNS configuration available to this process |
| dig to Tailscale resolver and public resolver | Socket bind denied: Operation not permitted |
| Direct TCP to 1.1.1.1:443 | PermissionError / EPERM |
| Direct TCP to Tailscale resolver 100.100.100.100:53 | PermissionError / EPERM |

Thus DNS lookup failure is one symptom of the command sandbox's network restriction.
Changing the Mac's normal DNS servers is not justified by this evidence. Hosted search
or other applications working does not establish command-sandbox connectivity.

Official [approval/network documentation](https://learn.chatgpt.com/docs/agent-approvals-security)
describes command networking separately from hosted search, apps and MCP. The
[permission documentation](https://learn.chatgpt.com/docs/permissions) also describes
the additional private-network guard when a network proxy is active. A grant for public
GitHub access need not automatically permit a Tailscale model endpoint.

The remedy is a client/administrator network grant for this command execution profile,
including the intended GitHub and Mac Studio destinations. This agent cannot grant
itself broader sandbox permissions. No fix is claimed until DNS, GitHub API access and
an actual Qwen response are successfully retested in the intended execution context.

## Queue state

Three research tasks and an integration task were created. The three workers currently
report `waitingOnApproval`. Their last pending actions are internal progress messages
back to the parent task using `send_message_to_thread`; this is distinct from the
network restriction and from a reverse-engineering blocker. They have performed initial
static analysis but are not verified progressing unattended past those approvals.
Do not describe a queued task as completed or actively making progress from its title
or an `active` label alone. Clear the client approvals or use an execution path whose
permissions cover the authorized work; do not bypass a pending approval.
