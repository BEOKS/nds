#!/usr/bin/env python3
"""
connections.py 단위 테스트
pytest로 MCP 연결 관리 기능 검증
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from connections import (
    MCPConnection,
    MCPConnectionStdio,
    MCPConnectionSSE,
    MCPConnectionHTTP,
    create_connection,
)


class TestMCPConnectionStdio:
    """MCPConnectionStdio 클래스 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        conn = MCPConnectionStdio("python", ["script.py"], {"KEY": "value"})

        assert conn.command == "python"
        assert conn.args == ["script.py"]
        assert conn.env == {"KEY": "value"}
        assert conn.session is None

    def test_initialization_without_args(self):
        """args 없이 초기화 테스트"""
        conn = MCPConnectionStdio("python")

        assert conn.args == []
        assert conn.env is None

    @pytest.mark.asyncio
    async def test_create_context(self):
        """_create_context 호출 테스트"""
        conn = MCPConnectionStdio("python", ["script.py"])

        with patch('connections.stdio_client') as mock_stdio:
            mock_stdio.return_value = MagicMock()
            conn._create_context()

            # stdio_client가 호출되었는지 확인
            mock_stdio.assert_called_once()
            call_args = mock_stdio.call_args[0][0]
            assert call_args.command == "python"
            assert call_args.args == ["script.py"]


class TestMCPConnectionSSE:
    """MCPConnectionSSE 클래스 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        headers = {"Authorization": "Bearer token"}
        conn = MCPConnectionSSE("https://example.com/mcp", headers)

        assert conn.url == "https://example.com/mcp"
        assert conn.headers == headers
        assert conn.session is None

    def test_initialization_without_headers(self):
        """헤더 없이 초기화 테스트"""
        conn = MCPConnectionSSE("https://example.com/mcp")

        assert conn.headers == {}

    @pytest.mark.asyncio
    async def test_create_context(self):
        """_create_context 호출 테스트"""
        conn = MCPConnectionSSE("https://example.com/mcp", {"Auth": "token"})

        with patch('connections.sse_client') as mock_sse:
            mock_sse.return_value = MagicMock()
            conn._create_context()

            # sse_client가 호출되었는지 확인
            mock_sse.assert_called_once_with(
                url="https://example.com/mcp",
                headers={"Auth": "token"}
            )


class TestMCPConnectionHTTP:
    """MCPConnectionHTTP 클래스 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        headers = {"Content-Type": "application/json"}
        conn = MCPConnectionHTTP("https://example.com/api", headers)

        assert conn.url == "https://example.com/api"
        assert conn.headers == headers
        assert conn.session is None

    def test_initialization_without_headers(self):
        """헤더 없이 초기화 테스트"""
        conn = MCPConnectionHTTP("https://example.com/api")

        assert conn.headers == {}

    @pytest.mark.asyncio
    async def test_create_context(self):
        """_create_context 호출 테스트"""
        conn = MCPConnectionHTTP("https://example.com/api", {"Auth": "key"})

        with patch('connections.streamablehttp_client') as mock_http:
            mock_http.return_value = MagicMock()
            conn._create_context()

            # streamablehttp_client가 호출되었는지 확인
            mock_http.assert_called_once_with(
                url="https://example.com/api",
                headers={"Auth": "key"}
            )


@pytest.mark.asyncio
class TestMCPConnectionContextManager:
    """MCPConnection 컨텍스트 매니저 테스트"""

    async def test_aenter_with_two_values(self):
        """__aenter__에서 2개 값 반환 테스트"""
        conn = MCPConnectionStdio("python")

        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_session = AsyncMock()

        with patch.object(conn, '_create_context') as mock_ctx, \
             patch('connections.AsyncExitStack') as mock_stack_cls, \
             patch('connections.ClientSession') as mock_session_cls:

            mock_stack = AsyncMock()
            mock_stack_cls.return_value = mock_stack
            mock_stack.enter_async_context.side_effect = [
                (mock_read, mock_write),
                mock_session
            ]

            mock_session.initialize = AsyncMock()

            result = await conn.__aenter__()

            assert result == conn
            assert conn.session == mock_session

    async def test_aenter_with_three_values(self):
        """__aenter__에서 3개 값 반환 테스트"""
        conn = MCPConnectionStdio("python")

        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_extra = MagicMock()
        mock_session = AsyncMock()

        with patch.object(conn, '_create_context') as mock_ctx, \
             patch('connections.AsyncExitStack') as mock_stack_cls, \
             patch('connections.ClientSession') as mock_session_cls:

            mock_stack = AsyncMock()
            mock_stack_cls.return_value = mock_stack
            mock_stack.enter_async_context.side_effect = [
                (mock_read, mock_write, mock_extra),
                mock_session
            ]

            mock_session.initialize = AsyncMock()

            result = await conn.__aenter__()

            assert result == conn
            assert conn.session == mock_session

    async def test_aenter_with_invalid_result(self):
        """__aenter__에서 잘못된 결과 반환 테스트"""
        conn = MCPConnectionStdio("python")

        with patch.object(conn, '_create_context') as mock_ctx, \
             patch('connections.AsyncExitStack') as mock_stack_cls:

            mock_stack = AsyncMock()
            mock_stack_cls.return_value = mock_stack
            mock_stack.enter_async_context.return_value = "invalid"

            with pytest.raises(ValueError, match="Unexpected context result"):
                await conn.__aenter__()

    async def test_aexit(self):
        """__aexit__ 테스트"""
        conn = MCPConnectionStdio("python")
        mock_stack = AsyncMock()
        conn._stack = mock_stack
        conn.session = MagicMock()

        await conn.__aexit__(None, None, None)

        # 스택이 정리되었는지 확인
        mock_stack.__aexit__.assert_called_once()
        assert conn.session is None
        assert conn._stack is None


@pytest.mark.asyncio
class TestMCPConnectionMethods:
    """MCPConnection 메서드 테스트"""

    async def test_list_tools(self):
        """list_tools 메서드 테스트"""
        conn = MCPConnectionStdio("python")
        mock_session = AsyncMock()

        # Mock tool 객체
        tool1 = MagicMock()
        tool1.name = "tool1"
        tool1.description = "First tool"
        tool1.inputSchema = {"type": "object"}

        tool2 = MagicMock()
        tool2.name = "tool2"
        tool2.description = "Second tool"
        tool2.inputSchema = {"type": "string"}

        mock_response = MagicMock()
        mock_response.tools = [tool1, tool2]

        mock_session.list_tools.return_value = mock_response
        conn.session = mock_session

        result = await conn.list_tools()

        assert len(result) == 2
        assert result[0]["name"] == "tool1"
        assert result[0]["description"] == "First tool"
        assert result[1]["name"] == "tool2"

    async def test_call_tool(self):
        """call_tool 메서드 테스트"""
        conn = MCPConnectionStdio("python")
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.content = {"output": "success"}

        mock_session.call_tool.return_value = mock_result
        conn.session = mock_session

        result = await conn.call_tool("test_tool", {"arg": "value"})

        assert result == {"output": "success"}
        mock_session.call_tool.assert_called_once_with(
            "test_tool",
            arguments={"arg": "value"}
        )


class TestCreateConnection:
    """create_connection 함수 테스트"""

    def test_create_stdio_connection(self):
        """stdio 연결 생성 테스트"""
        conn = create_connection(
            transport="stdio",
            command="python",
            args=["script.py"],
            env={"KEY": "value"}
        )

        assert isinstance(conn, MCPConnectionStdio)
        assert conn.command == "python"
        assert conn.args == ["script.py"]
        assert conn.env == {"KEY": "value"}

    def test_create_stdio_without_command(self):
        """command 없이 stdio 연결 생성 테스트"""
        with pytest.raises(ValueError, match="Command is required"):
            create_connection(transport="stdio")

    def test_create_sse_connection(self):
        """SSE 연결 생성 테스트"""
        conn = create_connection(
            transport="sse",
            url="https://example.com/mcp",
            headers={"Auth": "token"}
        )

        assert isinstance(conn, MCPConnectionSSE)
        assert conn.url == "https://example.com/mcp"
        assert conn.headers == {"Auth": "token"}

    def test_create_sse_without_url(self):
        """URL 없이 SSE 연결 생성 테스트"""
        with pytest.raises(ValueError, match="URL is required"):
            create_connection(transport="sse")

    def test_create_http_connection(self):
        """HTTP 연결 생성 테스트"""
        conn = create_connection(
            transport="http",
            url="https://example.com/api",
            headers={"Content-Type": "application/json"}
        )

        assert isinstance(conn, MCPConnectionHTTP)
        assert conn.url == "https://example.com/api"

    def test_create_streamable_http_connection(self):
        """streamable_http 연결 생성 테스트 (별칭)"""
        conn = create_connection(
            transport="streamable-http",
            url="https://example.com/api"
        )

        assert isinstance(conn, MCPConnectionHTTP)

    def test_create_http_without_url(self):
        """URL 없이 HTTP 연결 생성 테스트"""
        with pytest.raises(ValueError, match="URL is required"):
            create_connection(transport="http")

    def test_unsupported_transport(self):
        """지원되지 않는 전송 타입 테스트"""
        with pytest.raises(ValueError, match="Unsupported transport type"):
            create_connection(transport="websocket")

    def test_case_insensitive_transport(self):
        """대소문자 무관한 전송 타입 테스트"""
        conn = create_connection(
            transport="STDIO",
            command="python"
        )

        assert isinstance(conn, MCPConnectionStdio)


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_empty_command(self):
        """빈 command로 stdio 연결 생성 테스트"""
        with pytest.raises(ValueError):
            create_connection(transport="stdio", command="")

    def test_empty_url(self):
        """빈 URL로 SSE 연결 생성 테스트"""
        with pytest.raises(ValueError):
            create_connection(transport="sse", url="")

    def test_none_headers(self):
        """None 헤더로 연결 생성 테스트"""
        conn = create_connection(
            transport="sse",
            url="https://example.com",
            headers=None
        )

        assert conn.headers == {}

    def test_none_env(self):
        """None 환경변수로 stdio 연결 생성 테스트"""
        conn = create_connection(
            transport="stdio",
            command="python",
            env=None
        )

        assert conn.env is None

    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self):
        """에러 발생 시 세션 정리 테스트"""
        conn = MCPConnectionStdio("python")

        with patch.object(conn, '_create_context') as mock_ctx, \
             patch('connections.AsyncExitStack') as mock_stack_cls:

            mock_stack = AsyncMock()
            mock_stack_cls.return_value = mock_stack
            mock_stack.enter_async_context.side_effect = Exception("Connection failed")

            with pytest.raises(Exception, match="Connection failed"):
                await conn.__aenter__()

            # 에러 발생 시 스택 정리 확인
            mock_stack.__aexit__.assert_called_once()
