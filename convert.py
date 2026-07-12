#!/usr/bin/env python3
"""Convert TopChina's Clash proxy list into a Surge managed profile."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import yaml


DEFAULT_SOURCE = (
    "https://raw.githubusercontent.com/TopChina/proxy-list/refs/heads/main/"
    "clash_sub.yaml"
)
DEFAULT_OUTPUT = "surge.conf"
DEFAULT_TEST_URL = "http://www.gstatic.com/generate_204"


def fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "surge-proxy-list-converter/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def required_text(proxy: dict[str, Any], key: str) -> str:
    value = str(proxy.get(key, "")).strip()
    if not value:
        raise ValueError(f"Proxy {proxy.get('name', '<unnamed>')} is missing {key}")
    if any(character in value for character in (",", "\n", "\r")):
        raise ValueError(
            f"Proxy {proxy.get('name', '<unnamed>')} has an unsupported {key} value"
        )
    return value


def surge_proxy_line(proxy: dict[str, Any]) -> tuple[str, str]:
    name = required_text(proxy, "name")
    proxy_type = required_text(proxy, "type").lower()
    server = required_text(proxy, "server")
    port = int(proxy["port"])
    if not 1 <= port <= 65535:
        raise ValueError(f"Proxy {name} has an invalid port: {port}")

    tls = bool(proxy.get("tls", False))
    if proxy_type == "http":
        surge_type = "https" if tls else "http"
    elif proxy_type in {"socks5", "socks"}:
        surge_type = "socks5-tls" if tls else "socks5"
    else:
        raise ValueError(f"Proxy {name} uses unsupported type: {proxy_type}")

    parts = [surge_type, server, str(port)]
    username = proxy.get("username")
    password = proxy.get("password")
    if username is not None or password is not None:
        parts.extend(
            [
                f"username={required_text(proxy, 'username')}",
                f"password={required_text(proxy, 'password')}",
            ]
        )
    return name, f"{name} = {', '.join(parts)}"


def build_profile(source_text: str, source_url: str) -> str:
    document = yaml.safe_load(source_text)
    if not isinstance(document, dict):
        raise ValueError("The upstream YAML root must be a mapping")

    proxies = document.get("proxies")
    if not isinstance(proxies, list) or not proxies:
        raise ValueError("The upstream YAML contains no proxies")

    proxy_lines: list[str] = []
    proxy_names: list[str] = []
    for proxy in proxies:
        if not isinstance(proxy, dict):
            raise ValueError("Every proxy entry must be a mapping")
        name, line = surge_proxy_line(proxy)
        if name in proxy_names:
            raise ValueError(f"Duplicate proxy name: {name}")
        proxy_names.append(name)
        proxy_lines.append(line)

    source_time_match = re.search(r"^#\s*生成时间:\s*(.+)$", source_text, re.MULTILINE)
    source_time = source_time_match.group(1).strip() if source_time_match else "unknown"

    groups = document.get("proxy-groups") or []
    group_lines: list[str] = []
    known_policies = set(proxy_names) | {"DIRECT", "REJECT"}
    for group in groups:
        if not isinstance(group, dict):
            raise ValueError("Every proxy group must be a mapping")
        name = required_text(group, "name")
        group_type = required_text(group, "type").lower()
        members = group.get("proxies")
        if not isinstance(members, list) or not members:
            raise ValueError(f"Proxy group {name} has no members")
        member_names = [str(member) for member in members]

        if group_type == "select":
            line_parts = ["select", *member_names]
        elif group_type == "url-test":
            line_parts = ["url-test", *member_names]
            test_url = str(group.get("url") or DEFAULT_TEST_URL)
            line_parts.append(f"url={test_url}")
            if "interval" in group:
                line_parts.append(f"interval={int(group['interval'])}")
            if "tolerance" in group:
                line_parts.append(f"tolerance={int(group['tolerance'])}")
        else:
            raise ValueError(f"Proxy group {name} uses unsupported type: {group_type}")

        group_lines.append(f"{name} = {', '.join(line_parts)}")
        known_policies.add(name)

    rules = document.get("rules") or []
    rule_lines: list[str] = []
    for rule in rules:
        rule_text = str(rule).strip()
        if rule_text.startswith("MATCH,"):
            rule_text = "FINAL," + rule_text.removeprefix("MATCH,")
        rule_lines.append(rule_text)
    if not any(rule.startswith("FINAL,") for rule in rule_lines):
        rule_lines.append("FINAL,PROXY" if "PROXY" in known_policies else "FINAL,DIRECT")

    header = [
        "# Surge managed profile generated from TopChina/proxy-list",
        f"# Source: {source_url}",
        f"# Upstream generation time: {source_time}",
        f"# Proxy count: {len(proxy_lines)}",
        "# This file is generated automatically. Do not edit it by hand.",
        "",
    ]
    general = [
        "[General]",
        "loglevel = notify",
        "dns-server = system, 1.1.1.1, 8.8.8.8",
        f"proxy-test-url = {DEFAULT_TEST_URL}",
        "internet-test-url = http://www.gstatic.com/generate_204",
        "",
    ]
    sections = [
        *header,
        *general,
        "[Proxy]",
        *proxy_lines,
        "",
        "[Proxy Group]",
        *group_lines,
        "",
        "[Rule]",
        *rule_lines,
        "",
    ]
    return "\n".join(sections)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--input", type=Path, help="Read YAML from a local file")
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        source_text = (
            args.input.read_text(encoding="utf-8")
            if args.input
            else fetch_text(args.source)
        )
        profile = build_profile(source_text, args.source)
        args.output.write_text(profile, encoding="utf-8")
        print(f"Wrote {args.output} from {args.source}")
        return 0
    except Exception as error:
        print(f"Conversion failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
