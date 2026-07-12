import unittest

from convert import build_profile


FIXTURE = """# 生成时间: 2026-07-12 08:11 (GMT+8)
proxies:
  - name: Test-HTTP
    type: http
    server: 192.0.2.1
    port: 8080
    username: user
    password: pass
    tls: false
proxy-groups:
  - name: PROXY
    type: select
    proxies: [AUTO, Test-HTTP]
  - name: AUTO
    type: url-test
    proxies: [Test-HTTP]
    url: http://www.gstatic.com/generate_204
    interval: 300
    tolerance: 50
  - name: DIRECT-GROUP
    type: select
    proxies: [DIRECT, PROXY]
rules:
  - GEOIP,CN,DIRECT-GROUP
  - MATCH,PROXY
"""


class ConvertTest(unittest.TestCase):
    def test_builds_surge_profile(self) -> None:
        profile = build_profile(FIXTURE, "https://example.com/clash.yaml")

        self.assertIn("[Proxy]", profile)
        self.assertIn(
            "Test-HTTP = http, 192.0.2.1, 8080, username=user, password=pass",
            profile,
        )
        self.assertIn("PROXY = select, AUTO, Test-HTTP", profile)
        self.assertIn(
            "AUTO = url-test, Test-HTTP, url=http://www.gstatic.com/generate_204, "
            "interval=300, tolerance=50",
            profile,
        )
        self.assertIn("GEOIP,CN,DIRECT-GROUP", profile)
        self.assertIn("FINAL,PROXY", profile)


if __name__ == "__main__":
    unittest.main()
