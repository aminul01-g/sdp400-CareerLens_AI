"""The client address the rate limiter counts on.

Proposal section 7.5 asks for "token-based sessions, role-based access, input
validation", and the security section of the report claims the rate limit
"protects the password endpoints from guessing". Both are only true if the
address the limiter counts on is one the caller cannot choose.

``X-Forwarded-For`` is a client-supplied header. A server that believes it
unconditionally lets any caller put a different address in front of every
request, which turns a limit of ten password attempts a minute into an
unlimited number of them. These tests pin the behaviour that prevents that,
and the behaviour that has to keep working when a real proxy *is* in front of
the service.

The two halves matter equally. A fix that closed the hole by ignoring the
header everywhere would break every deployment that sits behind a proxy --
including the one this project is about to ship -- so the trusted-proxy path
is tested as carefully as the hostile one.
"""

from __future__ import annotations

from ipaddress import ip_network

import pytest

from app.core.config import get_settings
from app.core.request_context import (
    is_trusted_proxy,
    resolve_client_ip,
)

#: A proxy the deployment is told to believe.
TRUSTED = [ip_network("10.0.0.0/8")]


# --------------------------------------------------------------------------- #
# the default: believe nothing
# --------------------------------------------------------------------------- #
def test_without_configured_proxies_the_peer_is_the_client() -> None:
    """A direct connection has no proxy, so the peer is the client."""
    client, peer = resolve_client_ip("10.0.0.5", None)
    assert client == "10.0.0.5"
    assert peer == "10.0.0.5"


def test_an_unconfigured_deployment_ignores_the_forwarded_header() -> None:
    """The default is to believe no proxy, so the header is not consulted."""
    client, peer = resolve_client_ip("10.0.0.5", "1.2.3.4")
    assert client == "10.0.0.5"
    assert peer == "10.0.0.5"


def test_a_spoofed_header_cannot_mint_a_new_identity() -> None:
    """The attack the limiter has to withstand: rotate the header per request.

    Without a trusted proxy the header is ignored, so every request counts
    against the same bucket no matter what the caller claims.
    """
    first, _ = resolve_client_ip("10.0.0.5", "1.1.1.1")
    second, _ = resolve_client_ip("10.0.0.5", "2.2.2.2")
    third, _ = resolve_client_ip("10.0.0.5", "3.3.3.3")
    assert first == second == third == "10.0.0.5"


def test_a_chain_of_spoofed_entries_changes_nothing() -> None:
    client, _ = resolve_client_ip("10.0.0.5", "1.1.1.1, 2.2.2.2, 3.3.3.3")
    assert client == "10.0.0.5"


# --------------------------------------------------------------------------- #
# behind a trusted proxy
# --------------------------------------------------------------------------- #
def test_a_trusted_proxy_may_speak_for_its_client() -> None:
    """A proxy in the trusted list is believed: that is what it is for."""
    client, peer = resolve_client_ip("10.0.0.5", "203.0.113.9", TRUSTED)
    assert client == "203.0.113.9"
    assert peer == "10.0.0.5"


def test_the_chain_is_walked_from_the_right() -> None:
    """The rightmost untrusted entry is the client.

    Each proxy appends the address it saw, so the chain grows to the right.
    The client is the first entry that is not one of our own proxies.
    """
    client, _ = resolve_client_ip("10.0.0.5", "1.1.1.1, 203.0.113.9", TRUSTED)
    assert client == "203.0.113.9"


def test_an_untrusted_peer_cannot_impersonate_a_proxy() -> None:
    """Configuring trusted proxies must not make the header universally trusted.

    This is the case that matters on the public internet: the request did not
    arrive from our proxy, so whatever it claims in the header is the
    caller's own fabrication.
    """
    client, peer = resolve_client_ip("203.0.113.7", "1.2.3.4", TRUSTED)
    assert client == "203.0.113.7"
    assert peer == "203.0.113.7"


def test_a_client_supplied_prefix_is_discarded_even_behind_a_proxy() -> None:
    """A caller that prepends its own address cannot displace the real one.

    The proxy appends the address it saw to whatever the client sent, so the
    client's own entry is to the *left* of the truth. Walking from the right
    and taking the first untrusted entry discards it.
    """
    client, _ = resolve_client_ip("10.0.0.5", "6.6.6.6, 203.0.113.9", TRUSTED)
    assert client == "203.0.113.9"


def test_a_trusted_proxy_with_no_usable_header_falls_back_to_the_peer() -> None:
    client, peer = resolve_client_ip("10.0.0.5", None, TRUSTED)
    assert client == "10.0.0.5"
    assert peer == "10.0.0.5"


def test_a_header_of_only_trusted_proxies_falls_back_to_the_peer() -> None:
    client, _ = resolve_client_ip("10.0.0.5", "10.0.0.7", TRUSTED)
    assert client == "10.0.0.5"


def test_a_missing_peer_is_unknown() -> None:
    client, peer = resolve_client_ip(None, "1.2.3.4")
    assert client == "unknown"
    assert peer == "unknown"


# --------------------------------------------------------------------------- #
# trust matching
# --------------------------------------------------------------------------- #
def test_a_network_entry_matches_by_containment() -> None:
    assert is_trusted_proxy("10.1.2.3", TRUSTED)
    assert not is_trusted_proxy("11.1.2.3", TRUSTED)


def test_a_bare_address_entry_matches_only_itself() -> None:
    assert is_trusted_proxy("10.0.0.5", [ip_network("10.0.0.5")])
    assert not is_trusted_proxy("10.0.0.6", [ip_network("10.0.0.5")])


def test_an_unparseable_peer_is_never_trusted() -> None:
    assert not is_trusted_proxy("not-an-address", TRUSTED)
    assert not is_trusted_proxy("", TRUSTED)


def test_ipv6_is_supported() -> None:
    networks = [ip_network("2001:db8::/32")]
    assert is_trusted_proxy("2001:db8::1", networks)
    assert not is_trusted_proxy("2001:db9::1", networks)


# --------------------------------------------------------------------------- #
# the setting itself
# --------------------------------------------------------------------------- #
def test_the_default_trust_list_is_empty() -> None:
    """Nothing is trusted until a deployment says so."""
    assert get_settings().trusted_proxy_cidrs == ""


def test_the_trusted_networks_setting_parses_a_list() -> None:
    settings = get_settings().model_copy(
        update={"trusted_proxy_cidrs": "10.0.0.0/8, 192.168.0.0/16"}
    )
    networks = settings.trusted_proxy_networks
    assert len(networks) == 2
    assert is_trusted_proxy("10.1.1.1", networks)
    assert is_trusted_proxy("192.168.1.1", networks)
    assert not is_trusted_proxy("8.8.8.8", networks)


def test_a_malformed_trust_entry_is_skipped_rather_than_raising() -> None:
    """A typo in a deployment variable must not stop the API from booting.

    Skipping is also the safe direction: an entry that cannot be parsed is
    not a proxy we recognise, so it is not trusted.
    """
    settings = get_settings().model_copy(
        update={"trusted_proxy_cidrs": "10.0.0.0/8, not-a-network"}
    )
    networks = settings.trusted_proxy_networks
    assert len(networks) == 1
    assert is_trusted_proxy("10.1.1.1", networks)


def test_an_empty_trust_entry_is_ignored() -> None:
    settings = get_settings().model_copy(update={"trusted_proxy_cidrs": "  , 10.0.0.0/8 , "})
    assert len(settings.trusted_proxy_networks) == 1


@pytest.mark.parametrize("cidr", ["10.0.0.0/8", "192.168.1.0/24", "203.0.113.7"])
def test_every_configured_form_parses(cidr: str) -> None:
    settings = get_settings().model_copy(update={"trusted_proxy_cidrs": cidr})
    assert len(settings.trusted_proxy_networks) == 1
