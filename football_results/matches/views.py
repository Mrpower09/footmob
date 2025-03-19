from django.shortcuts import render, redirect
from django.http import JsonResponse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def validate_date(date_str):
    if len(date_str) != 8 or not date_str.isdigit():
        return False
    
    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])

    if year < 2020 or year > 2026:
        return False
    if month < 1 or month > 12:
        return False
    
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0): 
        days_in_month[1] = 29
    
    if day < 1 or day > days_in_month[month - 1]:
        return False
    
    return True

def fetch_live_data(date_str=None):
    import os
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/usr/src/app/browsers"
    
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")
    url = f"https://www.fotmob.com/?date={date_str}"

    # استفاده از Playwright به جای Selenium
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Headless برای لیارا
        page = browser.new_page()
        page.goto(url)
        
        # صبر کردن تا المنت‌های مورد نظر لود بشن
        page.wait_for_selector(".css-1lleae-CardCSS", timeout=30000)  # 30 ثانیه صبر
        
        # گرفتن محتوای صفحه
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "html.parser")

    leagues = {}
    card_elements = soup.select(".css-1lleae-CardCSS.e1mlfzv61")
    print(f"Number of cards found: {len(card_elements)}")

    for card in card_elements:
        group_title = card.select_one(".css-170egrx-GroupTitle.effkplk0")
        league_name = group_title.text.strip() if group_title else "Unknown League"
        
        league_logo_elem = card.select_one(".Image.LeagueIcon") or card.select_one(".Image.CountryIcon")
        league_logo = league_logo_elem['src'] if league_logo_elem else "https://via.placeholder.com/20"

        match_blocks = card.select(".css-e7gzg9-MatchWrapper.e112x9u91")
        print(f"Number of matches in card: {len(match_blocks)}")

        matches = []
        for match in match_blocks:
            home_team_elem = match.select_one(".css-9871a0-StatusAndHomeTeamWrapper .css-1o142s8-TeamName") or \
                            match.select_one(".css-9871a0-StatusAndHomeTeamWrapper span")
            away_team_elem = match.select_one(".css-gn249o-AwayTeamAndFollowWrapper .css-1o142s8-TeamName") or \
                            match.select_one(".css-gn249o-AwayTeamAndFollowWrapper span")
            
            status_wrapper = match.select_one(".css-k083tz-StatusLSMatchWrapperCSS") or match.select_one(".css-1k66icv-StatusLSMatchWrapperCSS")
            score_elem = status_wrapper.select_one(".css-baclne-LSMatchStatusScore") if status_wrapper else None
            status_elem = status_wrapper.select_one(".css-1s1h719-LSMatchStatusLive") if status_wrapper else None
            time_elem = status_wrapper.select_one(".css-ky5j63-LSMatchStatusTime") if status_wrapper else None
            ft_elem = match.select_one(".css-h4lrnf-StatusDotCSS") or status_wrapper.select_one(".css-1ubkvjq-LSMatchStatusReason") if status_wrapper else None
            home_logo_elem = match.select_one(".css-9871a0-StatusAndHomeTeamWrapper .Image.TeamIcon")
            away_logo_elem = match.select_one(".css-gn249o-AwayTeamAndFollowWrapper .Image.TeamIcon")

            home_team = home_team_elem.text.strip() if home_team_elem else (match.select_one(".css-9871a0-StatusAndHomeTeamWrapper") or {}).get_text(strip=True) or "N/A"
            away_team = away_team_elem.text.strip() if away_team_elem else (match.select_one(".css-gn249o-AwayTeamAndFollowWrapper") or {}).get_text(strip=True) or "N/A"
            score = score_elem.text.strip() if score_elem else "N/A"
            status_text = status_elem.text.strip() if status_elem else (ft_elem.text.strip() if ft_elem else "Unknown")
            time_text = time_elem.text.strip() if time_elem else ""

            is_postponed = status_text == "PP"
            if is_postponed and time_text:
                status = "PP"
                postponed_time = time_text
            elif time_elem and not status_elem and not ft_elem:
                status = time_text
                postponed_time = ""
            elif status_text == "Pen":
                status = "Pen"
                postponed_time = ""
            else:
                status = status_text
                postponed_time = ""

            home_logo = home_logo_elem['src'] if home_logo_elem else "https://via.placeholder.com/22"
            away_logo = away_logo_elem['src'] if away_logo_elem else "https://via.placeholder.com/22"

            home_score = ""
            away_score = ""
            if score != "N/A" and " - " in score:
                home_score, away_score = score.split(" - ")
            elif status_elem is None and time_elem and status_text != "PP":
                home_score = ""
                away_score = ""

            if home_score == "" or away_score == "":
                winner = "none"
            else:
                home_score_int = int(home_score)
                away_score_int = int(away_score)
                winner = "home" if home_score_int > away_score_int else "away" if away_score_int > home_score_int else "draw"

            matches.append({
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "status": status,
                "home_logo": home_logo,
                "away_logo": away_logo,
                "winner": winner,
                "is_postponed": is_postponed,
                "postponed_time": postponed_time,
            })

        leagues[league_name] = {
            "matches": matches,
            "logo": league_logo
        }

    return leagues, date_str

def live_matches(request):
    date_str = request.GET.get('date')
    if date_str and not validate_date(date_str):
        return render(request, 'matches/error.html', {'invalid_date': date_str})
    
    leagues, current_date = fetch_live_data(date_str)
    current_date_obj = datetime.strptime(current_date, "%Y%m%d")
    prev_date = (current_date_obj - timedelta(days=1)).strftime("%Y%m%d")
    next_date = (current_date_obj + timedelta(days=1)).strftime("%Y%m%d")
    
    context = {
        "leagues": leagues,
        "current_date": current_date,
        "prev_date": prev_date,
        "next_date": next_date,
    }
    return render(request, "matches/live_matches.html", context)

def live_matches_json(request):
    date_str = request.GET.get('date')
    if date_str and not validate_date(date_str):
        return JsonResponse({"error": "Invalid date format"}, status=400)
    
    leagues, _ = fetch_live_data(date_str)
    simplified_leagues = {league: data["matches"] for league, data in leagues.items()}
    return JsonResponse(simplified_leagues)