"""Per-request context that services and the audit log can read.

The audit log has to answer three questions about every change: **who** made
it, **when**, and **from where**. "Who" and "when" are arguments. "From where"
is ambient — it belongs to the request, not to the function that happens to be
recording the change.

Putting the client address in a :class:`~contextvars.ContextVar` solves that
without threading a ``Request`` object through every service function. The
middleware in ``app/main.py`` sets it once per request; ``audit_service`` reads
it when it writes a row. The service layer therefore records the *fact* of a
change and never has to know it is being audited.

The client address is **best-effort**, and the reason is worth stating
plainly, because getting it wrong is a security bug rather than a cosmetic
one.

``X-Forwarded-For`` is a comma-separated chain, oldest first, and the
**first** entry is nominally the original client. It is also entirely
client-supplied: a server that believes the header unconditionally lets any
caller put a different address in front of every request. That is harmless
for an audit log and fatal for a rate limiter — a limit of ten password
attempts a minute becomes unlimited if the attacker rotates the header.

So the header is believed only when the request actually arrived from a
proxy we have been told to trust. Otherwise the peer address is used, because
the peer is the one address the server can vouch for. The peer is always
recorded alongside the client, so the audit log keeps both facts and a reader
can see when they disagree.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextvars import ContextVar
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network

#: The union of the two network classes, for annotations. ``ip_network`` is the
#: *constructor*; these are the *types* it returns.
IPNetwork = IPv4Network | IPv6Network

#: The address the request appears to have come from.
client_ip_var: ContextVar[str] = ContextVar("client_ip", default="unknown")

#: The immediate peer — the proxy, when there is one.
peer_ip_var: ContextVar[str] = ContextVar("peer_ip", default="unknown")

#: How long a client address may be, in characters. Long enough for an IPv6
#: address with a zone index, short enough that it cannot hold anything else.
MAX_IP_LENGTH = 45


def current_client_ip() -> str:
    """The address the request appears to have come from, or ``"unknown"``."""
    return client_ip_var.get()


def current_peer_ip() -> str:
    """The immediate peer address — the proxy, when the deployment has one."""
    return peer_ip_var.get()


def _parse_address(value: str) -> IPv4Address | IPv6Address | IPNetwork | None:
    """Parse an address or network, or return ``None`` if it is not one."""
    try:
        return ip_address(value)
    except ValueError:
        pass
    try:
        return ip_network(value, strict=False)
    except ValueError:
        return None


def is_trusted_proxy(peer: str, trusted_networks: Iterable[IPNetwork]) -> bool:
    """Whether ``peer`` is an address we have been told to believe.

    A network entry matches by containment; a bare address matches only
    itself. An address that does not parse is not trusted — an unparseable
    peer is not a proxy we recognise.
    """
    if not trusted_networks:
        return False
    parsed = _parse_address(peer)
    if parsed is None:
        return False
    for network in trusted_networks:
        if isinstance(network, (IPv4Network, IPv6Network)):
            if isinstance(parsed, (IPv4Address, IPv6Address)) and parsed in network:
                return True
        elif parsed == network:
            return True
    return False


def resolve_client_ip(
    peer_host: str | None,
    forwarded_for: str | None,
    trusted_networks: Iterable[IPNetwork] = (),
) -> tuple[str, str]:
    """Work out the apparent client address and the peer address.

    Returns ``(client_ip, peer_ip)``.

    The peer address is always the address the request actually arrived
    from, and it is the answer whenever the peer is not a trusted proxy:
    the ``X-Forwarded-For`` header is client-supplied, and a server that
    believes it from an arbitrary peer lets a caller choose its own
    identity.

    When the peer *is* a trusted proxy, the header is believed — but only
    the part of it the proxy could not have been handed by the client. The
    chain is walked from the right, past every entry that is itself a
    trusted proxy, and the first untrusted entry is the client. That
    handles a chain of several proxies, each of which appends the address
    it saw. Anything to the left of that point was supplied by the client
    and is discarded.

    With no trusted proxies configured — the default, and the right default
    for a direct connection — the client address is the peer address.
    """
    peer = (peer_host or "").strip() or "unknown"
    if not is_trusted_proxy(peer, trusted_networks):
        return peer[:MAX_IP_LENGTH], peer[:MAX_IP_LENGTH]

    if forwarded_for:
        entries = [entry.strip() for entry in forwarded_for.split(",") if entry.strip()]
        # Walk from the right, past the entries our own proxies appended,
        # and take the first address that is not one of ours.
        for entry in reversed(entries):
            if is_trusted_proxy(entry, trusted_networks):
                continue
            return entry[:MAX_IP_LENGTH], peer[:MAX_IP_LENGTH]

    # A trusted proxy sent a header with nothing usable in it. The peer is
    # the only address left that the server can vouch for.
    return peer[:MAX_IP_LENGTH], peer[:MAX_IP_LENGTH]
