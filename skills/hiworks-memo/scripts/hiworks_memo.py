#!/usr/bin/env python3
"""
Hiworks Memo (쪽지) API Client

인증 방식 (우선순위):
  1. 크롬 브라우저 세션 쿠키 (browser_cookie3 사용)
     - 브라우저에서 hiworks.com에 로그인되어 있으면 자동으로 세션 사용
  2. 환경변수 기반 인증 (fallback)
     - HIWORKS_ID, HIWORKS_DOMAIN, HIWORKS_PWD 필요

환경변수:
  HIWORKS_ID       - 사용자 ID (이메일의 @ 앞부분) [fallback용]
  HIWORKS_DOMAIN   - 도메인 (예: company.com)
  HIWORKS_PWD      - 비밀번호 [fallback용]
  HIWORKS_OTP_SECRET - OTP 시크릿 (선택사항, TOTP 기반)
  HIWORKS_ENV      - 환경 (prod/dev/stage, 기본값: prod)
  HIWORKS_AUTH_MODE - 인증 모드 (cookie/env/auto, 기본값: auto)

사용법:
  python hiworks_memo.py list [--type received|sent] [--filter unread|is_star|has_attach] [--limit N]
  python hiworks_memo.py read <memo_no>
  python hiworks_memo.py count
"""

import argparse
import base64
import json
import os
import sys
from typing import Optional, Union
from urllib.parse import urlencode

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

try:
    import pyotp
    HAS_PYOTP = True
except ImportError:
    HAS_PYOTP = False

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    HAS_PYCRYPTODOME = True
except ImportError:
    HAS_PYCRYPTODOME = False


class HiworksCookieAuth:
    """크롬 브라우저 쿠키 기반 Hiworks 인증"""

    # 쿠키에서 추출할 도메인 목록
    COOKIE_DOMAINS = [
        ".hiworks.com",
        "hiworks.com",
        "office.hiworks.com",
        ".office.hiworks.com",
    ]

    # 도메인별 호스트 설정
    HOSTS = {
        "prod": {
            "messenger": "https://messenger.hiworks.com",
            "memo": "https://memo-api.office.hiworks.com",
        },
        "dev": {
            "messenger": "https://dev-messenger.hiworks.com",
            "memo": "https://memo-api.devoffice.hiworks.com",
        },
        "stage": {
            "messenger": "https://stage-messenger.hiworks.com",
            "memo": "https://memo-api.stageoffice.hiworks.com",
        },
    }

    GABIA_DOMAINS = {"gabia.com", "devapproval.com", "devapproval.shop"}
    GABIA_HOSTS = {
        "prod": {
            "messenger": "https://messenger.hiworks.com",
            "memo": "https://memo-api.gabiaoffice.hiworks.com",
        },
        "dev": {
            "messenger": "https://dev-messenger.hiworks.com",
            "memo": "https://memo-api.gabiaoffice.hiworks.com",
        },
        "stage": {
            "messenger": "https://stage-messenger.hiworks.com",
            "memo": "https://memo-api.gabiaoffice.hiworks.com",
        },
    }

    def __init__(self, domain: Optional[str] = None, env: str = "prod"):
        self.domain = domain
        self.env = env
        self.auth_key: Optional[str] = None
        self.office_no: Optional[str] = None
        self.basic_info_no: Optional[str] = None
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
        """쿠키에서 인증 정보 추출

        hiworks에서 사용하는 주요 쿠키:
        - OFFICE_SSO_TOKEN: SSO 토큰 (이걸로 auth_key 획득 가능)
        - hiworks_access_token: 액세스 토큰
        - HWENC: 암호화된 세션 정보
        """
        # 쿠키를 세션에 설정
        for name, value in cookies.items():
            self.session.cookies.set(name, value, domain=".hiworks.com")

        # SSO 토큰이 있으면 auth_key로 교환 시도
        sso_token = cookies.get("OFFICE_SSO_TOKEN")
        if sso_token:
            try:
                return self._exchange_sso_token(sso_token)
            except Exception as e:
                print(f"Warning: SSO 토큰 교환 실패 - {e}", file=sys.stderr)

        # 직접 API 호출로 세션 유효성 검증
        return self._validate_session_with_api()

    def _exchange_sso_token(self, sso_token: str) -> bool:
        """SSO 토큰으로 auth_key 획득"""
        # SSO 토큰을 사용해 사용자 정보 조회
        response = self.session.get(
            f"{self.hosts['messenger']}/messenger/user/info",
            headers={"Authorization": f"Bearer {sso_token}"},
        )

        if response.status_code == 200:
            try:
                data = response.json()
                if "auth_key" in data:
                    self.auth_key = data["auth_key"]
                    self.office_no = data.get("office_no")
                    self.basic_info_no = data.get("basic_info_no", self.office_no)
                    return True
            except json.JSONDecodeError:
                pass

        return False

    def _validate_session_with_api(self) -> bool:
        """쿠키 세션으로 직접 API 호출하여 유효성 검증

        쿠키 기반 인증에서는 Authorization 헤더 대신 쿠키를 사용
        """
        try:
            # 쪽지 수 조회 API로 세션 유효성 테스트
            response = self.session.get(
                f"{self.hosts['memo']}/memo/count",
            )

            if response.status_code == 200:
                # 쿠키 세션이 유효함 - auth_key 없이 쿠키로 인증
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

    def get_auth_headers(self) -> dict:
        """인증 헤더 반환

        쿠키 기반 인증에서는 세션 쿠키가 자동으로 전송됨
        auth_key가 있으면 기존 방식대로 Authorization 헤더 사용
        """
        if self.auth_key:
            return {
                "Authorization": f"Messenger {self.auth_key}",
                "X-Office-No": str(self.basic_info_no) if self.basic_info_no else "",
            }
        # 쿠키 기반 인증에서는 빈 헤더 반환 (쿠키가 자동 전송됨)
        return {}


class HiworksCrypto:
    """AES-256-CBC 암호화/복호화"""

    def __init__(self, app_no: str):
        if not HAS_PYCRYPTODOME:
            raise RuntimeError("pycryptodome가 설치되지 않음: pip install pycryptodome")
        # AES-256: 32바이트 키 필요 (app_no를 두 번 반복)
        self.key = (app_no + app_no).encode("utf-8")[:32]

    def generate_iv(self, length: int = 16) -> bytes:
        return os.urandom(length)

    def encrypt(self, plaintext: str, iv: bytes) -> str:
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        padded = pad(plaintext.encode("utf-8"), AES.block_size)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt(self, ciphertext: str, iv: bytes) -> str:
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(base64.b64decode(ciphertext))
        return unpad(decrypted, AES.block_size).decode("utf-8")


class HiworksAuth:
    """Hiworks 인증 클라이언트"""

    # 정적 앱 번호 (맥 메신저 package.json에서 가져옴)
    # 이 값은 AES-256-CBC 암호화 키로 사용됨
    # 맥 메신저에서는 16자리 전체를 사용함 (AppNo: "5fc0f03f4dc007d7")
    # AES-256-CBC는 32바이트 키가 필요하므로 이 값을 두 번 반복함
    STATIC_APP_NO = "5fc0f03f4dc007d7"  # 16자리

    HOSTS = {
        "prod": {
            "messenger": "https://messenger.hiworks.com",
            "memo": "https://memo-api.office.hiworks.com",
        },
        "dev": {
            "messenger": "https://dev-messenger.hiworks.com",
            "memo": "https://memo-api.devoffice.hiworks.com",
        },
        "stage": {
            "messenger": "https://stage-messenger.hiworks.com",
            "memo": "https://memo-api.stageoffice.hiworks.com",
        },
    }

    # 도메인별 호스트 설정 (gabia.com 계열은 다른 호스트 사용)
    GABIA_DOMAINS = {"gabia.com", "devapproval.com", "devapproval.shop"}
    GABIA_HOSTS = {
        "prod": {
            "messenger": "https://messenger.hiworks.com",
            "memo": "https://memo-api.gabiaoffice.hiworks.com",
        },
        "dev": {
            "messenger": "https://dev-messenger.hiworks.com",
            "memo": "https://memo-api.gabiaoffice.hiworks.com",
        },
        "stage": {
            "messenger": "https://stage-messenger.hiworks.com",
            "memo": "https://memo-api.gabiaoffice.hiworks.com",
        },
    }

    def __init__(
        self,
        user_id: str,
        domain: str,
        password: str,
        otp_secret: Optional[str] = None,
        env: str = "prod",
    ):
        self.user_id = user_id
        self.domain = domain
        self.password = password
        self.otp_secret = otp_secret
        self.env = env

        # 도메인에 따라 호스트 선택
        if domain in self.GABIA_DOMAINS:
            self.hosts = self.GABIA_HOSTS.get(env, self.GABIA_HOSTS["prod"])
        else:
            self.hosts = self.HOSTS.get(env, self.HOSTS["prod"])

        self.auth_key: Optional[str] = None
        self.user_seq: Optional[str] = None
        self.app_no: Optional[str] = None
        self.office_no: Optional[str] = None
        self.basic_info_no: Optional[str] = None  # X-Office-No 헤더에 사용
        self.crypto: Optional[HiworksCrypto] = None
        self.session = requests.Session()
        self.session.verify = False  # SSL 검증 비활성화 (사내 인증서)

    def _get_prefix_data(self) -> dict:
        """도메인 정보 조회 (app_no 획득)

        실제 맥 메신저에서는 정적 appNo를 사용해서 도메인을 암호화하여 전송함.
        """
        # 정적 app_no로 암호화 객체 생성
        crypto = HiworksCrypto(self.STATIC_APP_NO)
        iv = crypto.generate_iv()

        # v3.1 방식: 도메인을 암호화해서 전송
        data = {
            "key": base64.b64encode(iv).decode("utf-8"),
            "domain": crypto.encrypt(self.domain, iv),
            "key_type": "v3.1",
        }

        response = self.session.post(
            f"{self.hosts['messenger']}/wpf/gateway/getinfo_new",
            data=urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        # 응답이 암호화되어 있을 수 있음
        try:
            # 먼저 JSON으로 파싱 시도
            return response.json()
        except json.JSONDecodeError:
            # 암호화된 응답인 경우 복호화
            try:
                decrypted = crypto.decrypt(response.text, iv)
                return json.loads(decrypted)
            except Exception:
                # 복호화도 실패하면 원본 텍스트 반환
                return {"raw_response": response.text}

    def _get_otp_code(self) -> str:
        """TOTP 코드 생성"""
        if not self.otp_secret:
            return ""
        if not HAS_PYOTP:
            raise RuntimeError("pyotp가 설치되지 않음: pip install pyotp")
        totp = pyotp.TOTP(self.otp_secret)
        return totp.now()

    def login(self) -> bool:
        """로그인 및 auth_key 획득"""
        try:
            # 1. Prefix 데이터 조회 (app_no 획득)
            prefix_data = self._get_prefix_data()

            # app_no를 응답에서 가져오거나, 없으면 정적 값 사용
            # 맥 메신저에서는 16자리 전체를 사용함 (AES-256 키로 사용하려면 16자리 필요)
            self.app_no = prefix_data.get("app_no", "")
            if self.app_no:
                # 16자리까지만 사용 (AES-256-CBC 키 생성에 필요)
                self.app_no = self.app_no[:16]
            else:
                # 응답에서 app_no를 못 받으면 정적 값 사용
                self.app_no = self.STATIC_APP_NO
                print(
                    f"Info: API에서 app_no를 받지 못해 정적 값 사용: {self.app_no}",
                    file=sys.stderr,
                )

            self.crypto = HiworksCrypto(self.app_no)
            iv = self.crypto.generate_iv()

            # 2. 비밀번호 암호화
            encrypted_pwd = self.crypto.encrypt(self.password, iv)

            # 3. make_key 요청
            otp_code = self._get_otp_code()
            endpoint = "/make_key_otp" if otp_code else "/make_key"

            data = {
                "key": base64.b64encode(iv).decode("utf-8"),
                "user_id": self.crypto.encrypt(self.user_id, iv),
                "domain": self.crypto.encrypt(self.domain, iv),
                "user_pwd": encrypted_pwd,
                "key_type": "v3.1",
            }

            if otp_code:
                data["user_otp_code"] = self.crypto.encrypt(otp_code, iv)

            response = self.session.post(
                f"{self.hosts['messenger']}/wpf/main/multi{endpoint}",
                data=urlencode(data),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            # 응답 복호화
            result_str = self.crypto.decrypt(response.text, iv)
            result = json.loads(result_str)

            # 응답이 data 배열 안에 있을 수 있음
            if "data" in result and isinstance(result["data"], list):
                result = result["data"][0] if result["data"] else {}

            if result.get("result") == "TRUE":
                self.auth_key = result.get("auth_key")
                self.user_seq = result.get("master_user_no")
                self.office_no = result.get("office_no")
                # basic_info_no가 있으면 저장 (X-Office-No 헤더에 사용)
                self.basic_info_no = result.get("basic_info_no", self.office_no)
                return True
            elif result.get("result") == "REQUEST_OTP":
                print(
                    "Error: OTP가 필요합니다. HIWORKS_OTP_SECRET을 설정하세요.",
                    file=sys.stderr,
                )
                return False
            else:
                print(f"Error: 로그인 실패 - {result}", file=sys.stderr)
                return False

        except Exception as e:
            print(f"Error: 로그인 중 오류 발생 - {e}", file=sys.stderr)
            return False

    def get_auth_headers(self) -> dict:
        """인증 헤더 반환

        맥 메신저의 NetworkManager.js 참조:
        - Authorization: 'Messenger ' + authKey
        - X-Office-No: selectedBasicInfoNo (또는 office_no)
        """
        return {
            "Authorization": f"Messenger {self.auth_key}",
            "X-Office-No": str(self.basic_info_no) if self.basic_info_no else "",
        }


class HiworksMemo:
    """Hiworks 쪽지 API 클라이언트"""

    def __init__(self, auth: Union[HiworksAuth, HiworksCookieAuth]):
        self.auth = auth
        self.base_url = auth.hosts["memo"]
        self.session = auth.session

    def get_list(
        self,
        memo_type: str = "",
        filter_type: str = "",
        offset: int = 0,
        limit: int = 20,
        order: str = "desc",
    ) -> dict:
        """쪽지 목록 조회"""
        params = {
            "sort[id.no]": order,
            "page[offset]": offset,
            "page[limit]": limit,
        }

        if memo_type:
            params["filter[type]"] = memo_type
        if filter_type == "unread":
            params["filter[is_read]"] = "false"
        elif filter_type == "is_star":
            params["filter[is_star]"] = "true"
        elif filter_type == "has_attach":
            params["filter[has_attach]"] = "true"

        response = self.session.get(
            f"{self.base_url}/memo",
            params=params,
            headers=self.auth.get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_memo(self, memo_no: int, memo_type: str = "") -> dict:
        """쪽지 상세 조회"""
        if memo_type == "messages":
            path = f"/memo/messages/{memo_no}"
        else:
            path = f"/memo/{memo_no}"

        response = self.session.get(
            f"{self.base_url}{path}",
            headers=self.auth.get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    def get_count(self) -> dict:
        """읽지 않은 쪽지 수 조회"""
        response = self.session.get(
            f"{self.base_url}/memo/count",
            headers=self.auth.get_auth_headers(),
        )
        response.raise_for_status()
        return response.json()


def get_env_or_error(name: str) -> str:
    """환경변수 조회 (필수)"""
    value = os.environ.get(name)
    if not value:
        print(f"Error: 환경변수 {name}이(가) 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    return value


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


def try_env_auth(env: str) -> Optional[HiworksAuth]:
    """환경변수 기반 인증 시도"""
    user_id = os.environ.get("HIWORKS_ID")
    domain = os.environ.get("HIWORKS_DOMAIN")
    password = os.environ.get("HIWORKS_PWD")
    otp_secret = os.environ.get("HIWORKS_OTP_SECRET")

    if not all([user_id, domain, password]):
        return None

    if not HAS_PYCRYPTODOME:
        print("Warning: 환경변수 인증에 pycryptodome 필요: pip install pycryptodome", file=sys.stderr)
        return None

    auth = HiworksAuth(user_id, domain, password, otp_secret, env)
    try:
        if auth.login():
            print("Info: 환경변수 기반 인증됨", file=sys.stderr)
            return auth
    except Exception as e:
        print(f"Warning: 환경변수 인증 실패 - {e}", file=sys.stderr)

    return None


def main():
    parser = argparse.ArgumentParser(description="Hiworks 쪽지 API 클라이언트")
    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # list 명령어
    list_parser = subparsers.add_parser("list", help="쪽지 목록 조회")
    list_parser.add_argument(
        "--type", choices=["recv", "send"], default="", help="쪽지 유형 (recv: 받은 쪽지, send: 보낸 쪽지)"
    )
    list_parser.add_argument(
        "--filter",
        choices=["unread", "is_star", "has_attach"],
        default="",
        help="필터",
    )
    list_parser.add_argument("--limit", type=int, default=20, help="조회 개수")
    list_parser.add_argument("--offset", type=int, default=0, help="시작 위치")

    # read 명령어
    read_parser = subparsers.add_parser("read", help="쪽지 상세 조회")
    read_parser.add_argument("memo_no", type=int, help="쪽지 번호 (messages_no 권장)")
    read_parser.add_argument(
        "--raw", action="store_true", help="개별 쪽지 번호(no)로 조회 (/memo/<no>)"
    )

    # count 명령어
    subparsers.add_parser("count", help="읽지 않은 쪽지 수 조회")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 환경변수 조회
    domain = os.environ.get("HIWORKS_DOMAIN")
    env = os.environ.get("HIWORKS_ENV", "prod")
    auth_mode = os.environ.get("HIWORKS_AUTH_MODE", "auto")  # cookie, env, auto

    auth = None

    # 인증 방식 선택
    if auth_mode == "cookie":
        # 쿠키 인증만 사용
        auth = try_cookie_auth(domain, env)
        if not auth:
            print("Error: 쿠키 인증 실패. 브라우저에서 hiworks.com에 로그인하세요.", file=sys.stderr)
            sys.exit(1)

    elif auth_mode == "env":
        # 환경변수 인증만 사용
        auth = try_env_auth(env)
        if not auth:
            print("Error: 환경변수 인증 실패. HIWORKS_ID, HIWORKS_DOMAIN, HIWORKS_PWD를 설정하세요.", file=sys.stderr)
            sys.exit(1)

    else:  # auto (기본값)
        # 1. 먼저 쿠키 인증 시도
        auth = try_cookie_auth(domain, env)

        # 2. 실패하면 환경변수 인증 시도
        if not auth:
            auth = try_env_auth(env)

        # 3. 둘 다 실패
        if not auth:
            print("Error: 인증 실패", file=sys.stderr)
            print("", file=sys.stderr)
            print("방법 1) 크롬 브라우저에서 hiworks.com에 로그인하세요", file=sys.stderr)
            print("        pip install browser_cookie3", file=sys.stderr)
            print("", file=sys.stderr)
            print("방법 2) 환경변수를 설정하세요:", file=sys.stderr)
            print("        export HIWORKS_ID=<id>", file=sys.stderr)
            print("        export HIWORKS_DOMAIN=<domain>", file=sys.stderr)
            print("        export HIWORKS_PWD=<password>", file=sys.stderr)
            print("        pip install pycryptodome pyotp", file=sys.stderr)
            sys.exit(1)

    # 쪽지 API 클라이언트
    memo = HiworksMemo(auth)

    # 명령어 실행
    try:
        if args.command == "list":
            result = memo.get_list(
                memo_type=args.type,
                filter_type=args.filter,
                offset=args.offset,
                limit=args.limit,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "read":
            memo_type = "" if args.raw else "messages"
            result = memo.get_memo(args.memo_no, memo_type=memo_type)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "count":
            result = memo.get_count()
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except requests.HTTPError as e:
        print(f"Error: API 요청 실패 - {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
