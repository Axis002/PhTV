

import re
import sys
from urllib.parse import quote
from pathlib import Path

DEFAULT_UA = (
    "Mozilla/5.0 (Linux; Android 13; UltraBox Build/TP1A.220624.014; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
    "Chrome/136.0.7103.61 Mobile Safari/537.36"
)

SOURCE_URL = "https://raw.githubusercontent.com/ryansnetcafe/ott-playlist/refs/heads/main/ryansnetcafe.m3u"


def convert(content: str) -> str:
    lines = content.splitlines()
    output = []
    i = 0
    converted = 0
    plain = 0

    while i < len(lines):
        line = lines[i].rstrip()

        # Keep headers, group markers, empty lines
        if (
            line.startswith("#EXTM3U")
            or line.startswith("**********")
            or line.startswith("#EXTINF:-1 group-logo")
            or line.strip() == ""
        ):
            output.append(line)
            i += 1
            continue

        if line.startswith("#EXTINF:"):
            extinf = line
            props = {}
            stream_url = None
            j = i + 1

            while j < len(lines):
                next_line = lines[j].rstrip()
                if (
                    next_line.startswith("#EXTINF:")
                    or next_line.startswith("**********")
                    or next_line.startswith("#EXTM3U")
                ):
                    break
                if next_line.startswith("#KODIPROP:"):
                    prop = next_line[len("#KODIPROP:") :]
                    if "=" in prop:
                        k, v = prop.split("=", 1)
                        props[k.strip().lower()] = v.strip()
                    j += 1
                    continue
                if next_line.startswith("http://") or next_line.startswith("https://"):
                    stream_url = next_line
                    j += 1
                    break
                if next_line.strip() == "" or next_line.startswith("#"):
                    j += 1
                    continue
                j += 1

            if stream_url is None:
                output.append(extinf)
                i += 1
                continue

            # Extract clearkey
            clearkey = None
            for key in ("inputstream.adaptive.license_key", "license_key"):
                if key in props:
                    clearkey = props[key].strip()
                    break

            # Extract User-Agent from stream_headers
            ua = None
            headers_raw = props.get("inputstream.adaptive.stream_headers", "")
            if headers_raw:
                m = re.search(r"User-Agent=([^&]+)", headers_raw, re.I)
                if m:
                    ua = m.group(1).strip()

            # Handle URL that already has #clearkey
            if "#clearkey=" in stream_url:
                base, frag = stream_url.split("#", 1)
                stream_url = base
                if "clearkey=" in frag and not clearkey:
                    clearkey = frag.split("clearkey=")[1].split("&")[0]

            # Skip JSON-style keys (not supported cleanly)
            if clearkey and clearkey.startswith("{"):
                clearkey = None

            if clearkey:
                fragments = [f"clearkey={clearkey}"]
                if ua:
                    fragments.append(f"header=User-Agent:{quote(ua)}")
                elif "astro.com.my" in stream_url or "linearjitp" in stream_url:
                    fragments.append(f"header=User-Agent:{quote(DEFAULT_UA)}")

                new_url = stream_url + "#" + "&".join(fragments)
                output.append(extinf)
                output.append(new_url)
                converted += 1
            else:
                output.append(extinf)
                output.append(stream_url)
                plain += 1

            i = j
            continue

        output.append(line)
        i += 1

    print(f"Converted: {converted} | Plain: {plain} | Total lines: {len(output)}", file=sys.stderr)
    result = "\n".join(output) + "\n"
    # Brand as axis
    result = re.sub(r'billed-msg="[^"]*"', 'billed-msg="axis"', result, count=1)
    result = result.replace("M3U PLAYLIST BY: RYANSNETCAFE", "axis")
    return result


def main():
    import urllib.request

    print(f"Downloading {SOURCE_URL} ...", file=sys.stderr)
    with urllib.request.urlopen(SOURCE_URL, timeout=30) as resp:
        content = resp.read().decode("utf-8", errors="ignore")

    result = convert(content)

    out = Path("axis.m3u")
    out.write_text(result, encoding="utf-8")
    print(f"Written: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
