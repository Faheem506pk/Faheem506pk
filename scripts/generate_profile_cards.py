#!/usr/bin/env python3
import datetime as dt
import html
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request


USERNAME = os.getenv("GITHUB_USERNAME") or os.getenv("GH_USERNAME") or "Faheem506pk"
TOKEN = os.getenv("METRICS_TOKEN") or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
API_URL = "https://api.github.com"
CARD_BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#c9d1d9"
MUTED = "#8b949e"
BLUE = "#58a6ff"
GREEN = "#3fb950"
ORANGE = "#f0883e"
PINK = "#ff7b72"
PURPLE = "#bc8cff"
YELLOW = "#d29922"
LANG_COLORS = [ORANGE, BLUE, PINK, PURPLE, YELLOW, GREEN, "#39c5cf", "#a5d6ff"]


def request_json(path, params=None, method="GET", data=None):
    query = f"?{urllib.parse.urlencode(params)}" if params else ""
    url = f"{API_URL}{path}{query}"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "faheem506pk-profile-card-generator",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def graphql(query, variables):
    return request_json("/graphql", method="POST", data={"query": query, "variables": variables})


def paginated(path, params=None):
    params = dict(params or {})
    params["per_page"] = 100
    page = 1
    items = []
    while True:
        params["page"] = page
        batch = request_json(path, params)
        if not batch:
            return items
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def load_repositories():
    if TOKEN:
        repos = paginated(
            "/user/repos",
            {
                "visibility": "all",
                "affiliation": "owner",
                "sort": "updated",
            },
        )
        return [
            repo
            for repo in repos
            if repo.get("owner", {}).get("login", "").lower() == USERNAME.lower()
        ]
    return paginated(f"/users/{USERNAME}/repos", {"type": "owner", "sort": "updated"})


def load_contributions():
    if not TOKEN:
        return {}
    query = """
      query($login: String!, $from: DateTime!, $to: DateTime!) {
        user(login: $login) {
          contributionsCollection(from: $from, to: $to) {
            totalCommitContributions
            totalIssueContributions
            totalPullRequestContributions
            totalPullRequestReviewContributions
            totalRepositoryContributions
            restrictedContributionsCount
            contributionCalendar {
              totalContributions
            }
          }
        }
      }
    """
    now = dt.datetime.now(dt.timezone.utc)
    start = dt.datetime(now.year, 1, 1, tzinfo=dt.timezone.utc)
    data = graphql(
        query,
        {
            "login": USERNAME,
            "from": start.isoformat().replace("+00:00", "Z"),
            "to": now.isoformat().replace("+00:00", "Z"),
        },
    )
    collection = data.get("data", {}).get("user", {}).get("contributionsCollection", {})
    calendar = collection.get("contributionCalendar", {})
    return {
        "year": now.year,
        "total": calendar.get("totalContributions", 0),
        "commits": collection.get("totalCommitContributions", 0),
        "prs": collection.get("totalPullRequestContributions", 0),
        "reviews": collection.get("totalPullRequestReviewContributions", 0),
        "issues": collection.get("totalIssueContributions", 0),
        "repos": collection.get("totalRepositoryContributions", 0),
        "private": collection.get("restrictedContributionsCount", 0),
    }


def load_languages(repos):
    languages = {}
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        try:
            repo_langs = request_json(f"/repos/{repo['full_name']}/languages")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            continue
        for language, bytes_count in repo_langs.items():
            languages[language] = languages.get(language, 0) + bytes_count
    return dict(sorted(languages.items(), key=lambda item: item[1], reverse=True))


def format_number(value):
    return f"{value:,}"


def text(x, y, value, size=13, fill=TEXT, weight=400, anchor="start"):
    escaped = html.escape(str(value))
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        f'font-family="Segoe UI, Ubuntu, sans-serif" font-weight="{weight}" '
        f'text-anchor="{anchor}">{escaped}</text>'
    )


def stat_row(y, label, value, color=TEXT):
    return (
        f'{text(28, y, label, 13, MUTED)}'
        f'{text(292, y, value, 13, color, 600, "end")}'
    )


def write_stats_card(repos, contributions):
    stars = sum(repo.get("stargazers_count", 0) for repo in repos)
    forks = sum(repo.get("forks_count", 0) for repo in repos)
    public_repos = sum(1 for repo in repos if not repo.get("private"))
    language_count = len({repo.get("language") for repo in repos if repo.get("language")})
    updated_at = dt.datetime.now().strftime("%d %b %Y %H:%M")
    year = contributions.get("year", dt.datetime.now().year)
    contribution_value = contributions.get("total", "Token required")
    private_count = contributions.get("private", 0)

    svg = f'''<svg width="420" height="220" viewBox="0 0 420 220" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">GitHub profile stats for {html.escape(USERNAME)}</title>
  <desc id="desc">Generated from GitHub API data.</desc>
  <rect x="0.5" y="0.5" width="419" height="219" rx="8" fill="{CARD_BG}" stroke="{BORDER}"/>
  {text(24, 34, "Custom GitHub Stats", 18, BLUE, 600)}
  {text(24, 58, f"Updated {updated_at}", 11, MUTED)}
  {stat_row(88, "Total Stars", format_number(stars), YELLOW)}
  {stat_row(112, "Forks", format_number(forks), GREEN)}
  {stat_row(136, "Public Repositories", format_number(public_repos), TEXT)}
  {stat_row(160, f"{year} Contributions", format_number(contribution_value) if isinstance(contribution_value, int) else contribution_value, BLUE)}
  {stat_row(184, "Private Contributions", format_number(private_count), PURPLE)}
  {stat_row(208, "Languages Detected", format_number(language_count), ORANGE)}
</svg>
'''
    with open("profile-stats.svg", "w", encoding="utf-8") as file:
        file.write(svg)


def donut_segment(cx, cy, radius, start_angle, end_angle, color):
    large = 1 if end_angle - start_angle > 180 else 0
    start = polar(cx, cy, radius, end_angle)
    end = polar(cx, cy, radius, start_angle)
    return (
        f'<path d="M {start[0]:.2f} {start[1]:.2f} A {radius} {radius} 0 {large} 0 '
        f'{end[0]:.2f} {end[1]:.2f}" stroke="{color}" stroke-width="24" fill="none"/>'
    )


def polar(cx, cy, radius, angle):
    radians = (angle - 90) * 3.141592653589793 / 180
    return cx + radius * math.cos(radians), cy + radius * math.sin(radians)


def write_languages_card(languages):
    top_languages = list(languages.items())[:6]
    total = sum(value for _, value in top_languages) or 1
    angle = 0
    segments = []
    rows = []
    for index, (language, bytes_count) in enumerate(top_languages):
        percent = bytes_count / total * 100
        next_angle = angle + percent / 100 * 360
        color = LANG_COLORS[index % len(LANG_COLORS)]
        segments.append(donut_segment(315, 116, 52, angle, next_angle, color))
        rows.append(
            f'<rect x="28" y="{72 + index * 22}" width="10" height="10" rx="2" fill="{color}"/>'
            f'{text(46, 82 + index * 22, language, 13, TEXT)}'
            f'{text(214, 82 + index * 22, f"{percent:.1f}%", 13, MUTED, 600, "end")}'
        )
        angle = next_angle

    svg = f'''<svg width="420" height="220" viewBox="0 0 420 220" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Top languages for {html.escape(USERNAME)}</title>
  <desc id="desc">Generated from repository language byte totals available to the workflow token.</desc>
  <rect x="0.5" y="0.5" width="419" height="219" rx="8" fill="{CARD_BG}" stroke="{BORDER}"/>
  {text(24, 34, "Custom Top Languages", 18, BLUE, 600)}
  {text(24, 58, "By repository language bytes", 11, MUTED)}
  {''.join(rows)}
  <circle cx="315" cy="116" r="52" stroke="#161b22" stroke-width="24" fill="none"/>
  {''.join(segments)}
  <circle cx="315" cy="116" r="31" fill="{CARD_BG}"/>
</svg>
'''
    with open("profile-languages.svg", "w", encoding="utf-8") as file:
        file.write(svg)


def main():
    repos = load_repositories()
    contributions = load_contributions()
    languages = load_languages(repos)
    write_stats_card(repos, contributions)
    write_languages_card(languages)


if __name__ == "__main__":
    main()
