#!/usr/bin/env python3
"""
Hiworks Mail API Client

인증 방식 (우선순위):
  1. 크롬 브라우저 세션 쿠키 (browser_cookie3 사용)
     - 브라우저에서 hiworks.com에 로그인되어 있으면 자동으로 세션 사용
  2. 환경변수 기반 인증 (fallback)
     - HIWORKS_ID, HIWORKS_DOMAIN, HIWORKS_PWD 필요

환경변수:
  HIWORKS_DOMAIN   - 도메인 (예: company.com)
  HIWORKS_ENV      - 환경 (prod/dev/stage, 기본값: prod)
  HIWORKS_AUTH_MODE - 인증 모드 (cookie/env/auto, 기본값: auto)

사용법:
  python hiworks_mail.py mailboxes
  python hiworks_mail.py list [--mailbox b0] [--filter unread|starred|important] [--limit N]
  python hiworks_mail.py read <mail_no>
  python hiworks_mail.py count [--mailbox b0]
"""

import argparse
import html
import json
import os
import re
import sys
import webbrowser
from typing import Optional, Union

import requests
import urllib3

# SSL 경고 비활성화 (사내 인증서)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 선택적 의존성
try:
    import browser_cookie3
    HAS_BROWSER_COOKIE3 = True
except ImportError:
    HAS_BROWSER_COOKIE3 = False


class HiworksCookieAuth:
    """크롬 브라우저 쿠키 기반 Hiworks 인증"""

    GABIA_DOMAINS = {"gabia.com", "devapproval.com", "devapproval.shop"}

    # 도메인별 호스트 설정
    HOSTS = {
        "prod": {"mail": "https://mail-api.office.hiworks.com"},
        "dev": {"mail": "https://mail-api.devoffice.hiworks.com"},
        "stage": {"mail": "https://mail-api.stageoffice.hiworks.com"},
    }

    GABIA_HOSTS = {
        "prod": {"mail": "https://mail-api.gabiaoffice.hiworks.com"},
        "dev": {"mail": "https://mail-api.gabiaoffice.hiworks.com"},
        "stage": {"mail": "https://mail-api.gabiaoffice.hiworks.com"},
    }

    def __init__(self, domain: Optional[str] = None, env: str = "prod"):
        self.domain = domain
        self.env = env
        self.session = requests.Session()
        self.session.verify = False

        # 도메인에 따라 호스트 선택
        if domain and domain in self.GABIA_DOMAINS:
            self.hosts = self.GABIA_HOSTS.get(env, self.GABIA_HOSTS["prod"])
        else:
            self.hosts = self.HOSTS.get(env, self.HOSTS["prod"])

    def _get_chrome_cookies(self) -> dict:
        """크롬 브라우저에서 hiworks.com 쿠키 추출"""
        if not HAS_BROWSER_COOKIE3:
            raise RuntimeError("browser_cookie3가 설치되지 않음: pip install browser_cookie3")

        cookies = {}
        try:
            cj = browser_cookie3.chrome(domain_name=".hiworks.com")
            for cookie in cj:
                cookies[cookie.name] = cookie.value
        except Exception as e:
            print(f"Warning: Chrome 쿠키 추출 실패 - {e}", file=sys.stderr)

        return cookies

    def _extract_auth_from_cookies(self, cookies: dict) -> bool:
        """쿠키에서 인증 정보 추출"""
        # h_officeid 쿠키에서 도메인 자동 감지
        office_id = cookies.get("h_officeid")
        if office_id and not self.domain:
            self.domain = office_id
            # 도메인에 따라 호스트 재설정
            if self.domain in self.GABIA_DOMAINS:
                self.hosts = self.GABIA_HOSTS.get(self.env, self.GABIA_HOSTS["prod"])

        # 쿠키를 세션에 설정
        for name, value in cookies.items():
            self.session.cookies.set(name, value, domain=".hiworks.com")

        # API 호출로 세션 유효성 검증
        return self._validate_session_with_api()

    def _validate_session_with_api(self) -> bool:
        """쿠키 세션으로 직접 API 호출하여 유효성 검증"""
        try:
            response = self.session.get(f"{self.hosts['mail']}/v2/mailboxes")

            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                print("Error: 브라우저 세션이 만료됨. 브라우저에서 다시 로그인하세요.", file=sys.stderr)
                return False
            else:
                return False

        except Exception as e:
            print(f"Warning: 세션 검증 실패 - {e}", file=sys.stderr)
            return False

    def login(self) -> bool:
        """크롬 쿠키로 로그인 시도"""
        cookies = self._get_chrome_cookies()

        if not cookies:
            print("Error: 크롬에서 hiworks.com 쿠키를 찾을 수 없음", file=sys.stderr)
            print("Hint: 크롬 브라우저에서 hiworks.com에 로그인하세요", file=sys.stderr)
            return False

        return self._extract_auth_from_cookies(cookies)


class HiworksMail:
    """Hiworks 메일 API 클라이언트"""

    # 메일함 ID 매핑
    MAILBOX_NAMES = {
        "b0": "받은 메일함",
        "b1": "보낸 메일함",
        "b2": "보낼 메일함",
        "b3": "임시 메일함",
        "b4": "스팸 메일함",
        "b5": "휴지통",
    }

    def __init__(self, auth: HiworksCookieAuth):
        self.auth = auth
        self.base_url = auth.hosts["mail"]
        self.session = auth.session

    def get_mailboxes(self) -> dict:
        """메일함 목록 조회"""
        response = self.session.get(f"{self.base_url}/v2/mailboxes")
        response.raise_for_status()
        return response.json()

    def get_list(
        self,
        mailbox: str = "b0",
        filter_type: str = "",
        offset: int = 0,
        limit: int = 20,
    ) -> dict:
        """메일 목록 조회

        Args:
            mailbox: 메일함 ID (b0=받은편지함, b1=보낸편지함, b4=스팸, b5=휴지통)
            filter_type: 필터 (unread, starred, important)
            offset: 시작 위치
            limit: 조회 개수
        """
        params = {
            "mailbox": mailbox,
            "offset": offset,
            "limit": limit,
        }

        response = self.session.get(f"{self.base_url}/v2/mails", params=params)
        response.raise_for_status()
        data = response.json()

        # 필터링 (API에서 지원하지 않으므로 클라이언트에서 처리)
        if filter_type and data.get("data"):
            if filter_type == "unread":
                data["data"] = [m for m in data["data"] if m.get("is_new")]
            elif filter_type == "starred":
                data["data"] = [m for m in data["data"] if m.get("is_starred")]
            elif filter_type == "important":
                data["data"] = [m for m in data["data"] if m.get("is_important")]

        return data

    def get_mail(self, mail_no: int) -> dict:
        """메일 상세 조회"""
        response = self.session.get(f"{self.base_url}/v2/mails/{mail_no}")
        response.raise_for_status()
        return response.json()

    def get_unread_count(self, mailbox: str = "b0") -> dict:
        """읽지 않은 메일 수 조회 (목록 조회 후 계산)"""
        # 전체 메일 수
        params = {"mailbox": mailbox, "limit": 1}
        response = self.session.get(f"{self.base_url}/v2/mails", params=params)
        response.raise_for_status()
        data = response.json()
        total = data.get("meta", {}).get("page", {}).get("total", 0)

        # 안 읽은 메일 수 계산 (최근 100개 기준)
        params["limit"] = 100
        response = self.session.get(f"{self.base_url}/v2/mails", params=params)
        response.raise_for_status()
        data = response.json()
        unread = sum(1 for m in data.get("data", []) if m.get("is_new"))

        return {
            "data": {
                "mailbox": mailbox,
                "mailbox_name": self.MAILBOX_NAMES.get(mailbox, mailbox),
                "total": total,
                "unread_sample": unread,
                "sample_size": min(100, total),
            }
        }


def strip_html(text: str) -> str:
    """HTML 태그 제거 및 엔티티 디코딩"""
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text)


GABIA_DOMAINS = {"gabia.com", "devapproval.com", "devapproval.shop"}


def open_login_page(domain: Optional[str] = None) -> None:
    """브라우저에서 하이웍스 로그인 페이지 열기"""
    if domain and domain in GABIA_DOMAINS:
        login_url = f"https://login.gabiaoffice.hiworks.com/{domain}"
    elif domain:
        login_url = f"https://login.office.hiworks.com/{domain}"
    else:
        login_url = "https://office.hiworks.com"

    print(f"브라우저에서 로그인 페이지를 엽니다: {login_url}", file=sys.stderr)
    print("로그인 완료 후 다시 명령어를 실행하세요.", file=sys.stderr)
    webbrowser.open(login_url)


def try_cookie_auth(domain: Optional[str], env: str) -> Optional[HiworksCookieAuth]:
    """크롬 쿠키 기반 인증 시도"""
    if not HAS_BROWSER_COOKIE3:
        return None

    auth = HiworksCookieAuth(domain=domain, env=env)
    try:
        if auth.login():
            print("Info: 크롬 브라우저 세션으로 인증됨", file=sys.stderr)
            return auth
    except Exception as e:
        print(f"Warning: 쿠키 인증 실패 - {e}", file=sys.stderr)

    return None


def main():
    parser = argparse.ArgumentParser(description="Hiworks 메일 API 클라이언트")
    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # mailboxes 명령어
    subparsers.add_parser("mailboxes", help="메일함 목록 조회")

    # list 명령어
    list_parser = subparsers.add_parser("list", help="메일 목록 조회")
    list_parser.add_argument(
        "--mailbox", default="b0", help="메일함 ID (b0=받은편지함, b1=보낸편지함)"
    )
    list_parser.add_argument(
        "--filter",
        choices=["unread", "starred", "important"],
        default="",
        help="필터",
    )
    list_parser.add_argument("--limit", type=int, default=20, help="조회 개수")
    list_parser.add_argument("--offset", type=int, default=0, help="시작 위치")

    # read 명령어
    read_parser = subparsers.add_parser("read", help="메일 상세 조회")
    read_parser.add_argument("mail_no", type=int, help="메일 번호")
    read_parser.add_argument("--strip-html", action="store_true", help="HTML 태그 제거")

    # count 명령어
    count_parser = subparsers.add_parser("count", help="읽지 않은 메일 수 조회")
    count_parser.add_argument(
        "--mailbox", default="b0", help="메일함 ID (b0=받은편지함)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 환경변수 조회
    domain = os.environ.get("HIWORKS_DOMAIN")
    env = os.environ.get("HIWORKS_ENV", "prod")

    # 쿠키 인증 시도
    auth = try_cookie_auth(domain, env)
    if not auth:
        print("Error: 인증 실패 - 브라우저에서 로그인이 필요합니다.", file=sys.stderr)
        open_login_page(domain)
        sys.exit(1)

    # 메일 API 클라이언트
    mail = HiworksMail(auth)

    # 명령어 실행
    try:
        if args.command == "mailboxes":
            result = mail.get_mailboxes()
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "list":
            result = mail.get_list(
                mailbox=args.mailbox,
                filter_type=args.filter,
                offset=args.offset,
                limit=args.limit,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "read":
            result = mail.get_mail(args.mail_no)
            if args.strip_html:
                # text_content 필드 사용 (API에서 제공하는 plain text)
                data = result.get("data", {})
                msg = data.get("message", {})
                if msg.get("text_content"):
                    msg["content"] = msg["text_content"]
                elif msg.get("content"):
                    msg["content"] = strip_html(msg["content"])
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "count":
            result = mail.get_unread_count(args.mailbox)
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except requests.HTTPError as e:
        print(f"Error: API 요청 실패 - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
