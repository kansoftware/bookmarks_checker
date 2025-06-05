import asyncio
import ssl
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import aiohttp
import pytest
import pytest_asyncio

from src.core.checker import URLChecker, URLResponse


@pytest_asyncio.fixture
async def checker():
    async with URLChecker(timeout=1, max_retries=2) as c:
        yield c


@pytest.mark.asyncio
async def test_successful_request(checker):
    mock_response_cm = AsyncMock()
    mock_response_cm.status = 200
    mock_response_cm.headers = {"content-type": "text/html"}
    mock_response_cm.url = "http://example.com"
    mock_response_cm.__aenter__.return_value = mock_response_cm

    mock_get_method = AsyncMock(return_value=mock_response_cm)

    with patch("aiohttp.ClientSession.get", new=mock_get_method):
        result = await checker.check_url("http://example.com")

        assert result.is_available
        assert result.status == 200
        assert result.error is None
        assert result.response_time is not None
        assert result.retry_count == 0
        assert checker._metrics["successful_requests"] == 1


@pytest.mark.asyncio
async def test_timeout_error(checker):
    max_retries = checker.max_retries
    
    mock_response_cm = AsyncMock()
    mock_response_cm.__aenter__.side_effect = [asyncio.TimeoutError()] * max_retries
    
    mock_get_method = AsyncMock(return_value=mock_response_cm)

    with patch('aiohttp.ClientSession.get', new=mock_get_method):
        result = await checker.check_url('http://example.com')

        assert not result.is_available
        assert result.status == 0
        assert result.error == "Timeout"
        assert result.retry_count == max_retries


@pytest.mark.asyncio
async def test_network_error(checker):
    max_retries = checker.max_retries
    
    mock_response_cm = AsyncMock()
    mock_response_cm.__aenter__.side_effect = [aiohttp.ClientError()] * max_retries
    
    mock_get_method = AsyncMock(return_value=mock_response_cm)

    with patch('aiohttp.ClientSession.get', new=mock_get_method):
        result = await checker.check_url('http://example.com')

        assert not result.is_available
        assert result.status == 0
        assert "Network error" in result.error
        assert result.retry_count == max_retries


@pytest.mark.asyncio
async def test_ssl_error(checker):
    mock_response_cm = AsyncMock()
    mock_response_cm.__aenter__.side_effect = ssl.SSLError("SSL error")
    
    mock_get_method = AsyncMock(return_value=mock_response_cm)

    with patch("aiohttp.ClientSession.get", new=mock_get_method):
        result = await checker.safe_check_url("http://example.com")

        assert not result.is_available
        assert result.status == 0
        assert "SSL error" in result.error
        assert result.response_time is not None
        assert checker._metrics["ssl_errors"] == 1


@pytest.mark.asyncio
async def test_retry_mechanism(checker):
    max_retries = checker.max_retries
    
    response_cms = []
    for _ in range(max_retries - 1):
        error_response_cm = AsyncMock()
        error_response_cm.__aenter__.side_effect = aiohttp.ClientError()
        response_cms.append(error_response_cm)
        
    success_response_cm = AsyncMock()
    success_response_cm.status = 200
    success_response_cm.headers = {'content-type': 'text/html'}
    success_response_cm.url = "http://example.com"
    success_response_cm.__aenter__.return_value = success_response_cm 
    response_cms.append(success_response_cm)
    
    mock_get_method = AsyncMock(side_effect=response_cms)

    with patch('aiohttp.ClientSession.get', new=mock_get_method):
        result = await checker.check_url('http://example.com')

        assert result.is_available
        assert result.status == 200
        assert result.error is None
        assert result.retry_count == max_retries - 1


@pytest.mark.asyncio
async def test_metrics_collection(checker):
    urls = ["http://example1.com", "http://example2.com"]

    mock_inner_response = Mock(
        status=200, 
        headers={"content-type": "text/html"},
        url="http://example.com/final"
    )
    mock_response_cm = AsyncMock()
    mock_response_cm.__aenter__.return_value = mock_inner_response
    
    mock_get_method = AsyncMock(return_value=mock_response_cm)
    
    with patch("aiohttp.ClientSession.get", new=mock_get_method):
        results = await checker.check_urls(urls)

        metrics = checker.get_metrics()
        assert metrics["total_requests"] == 2
        assert metrics["successful_requests"] == 2
        assert metrics["failed_requests"] == 0
        assert len(results) == 2
        assert all(r.is_available for r in results)


@pytest.mark.asyncio
async def test_multiple_error_types(checker):
    urls = [
        "http://timeout.com",
        "http://network.com",
        "http://ssl.com",
        "http://success.com",
    ]

    response_cms_sequence = []

    for _ in range(checker.max_retries):
        cm = AsyncMock()
        cm.__aenter__.side_effect = asyncio.TimeoutError()
        response_cms_sequence.append(cm)
    for _ in range(checker.max_retries):
        cm = AsyncMock()
        cm.__aenter__.side_effect = aiohttp.ClientError()
        response_cms_sequence.append(cm)
    cm_ssl = AsyncMock()
    cm_ssl.__aenter__.side_effect = ssl.SSLError("SSL error")
    response_cms_sequence.append(cm_ssl)
    cm_success = AsyncMock()
    cm_success.status = 200
    cm_success.headers = {"content-type": "text/html"}
    cm_success.url = "http://success.com"
    cm_success.__aenter__.return_value = cm_success
    response_cms_sequence.append(cm_success)
    
    mock_get_method = AsyncMock(side_effect=response_cms_sequence)

    with patch("aiohttp.ClientSession.get", new=mock_get_method):
        results = await checker.check_urls(urls)

        metrics = checker.get_metrics()
        expected_total_requests = checker.max_retries + checker.max_retries + 1 + 1
        assert metrics["total_requests"] == expected_total_requests
        assert metrics["timeout_errors"] == 1
        assert metrics["network_errors"] == 1
        assert metrics["ssl_errors"] == 1
        assert metrics["successful_requests"] == 1


@pytest.mark.asyncio
async def test_response_time_measurement(checker):
    mock_response_cm = AsyncMock()
    mock_response_cm.__aenter__.return_value = Mock(
        status=200, headers={"content-type": "text/html"}
    )

    mock_get_method = AsyncMock(return_value=mock_response_cm)

    with patch("aiohttp.ClientSession.get", new=mock_get_method):
        result = await checker.check_url("http://example.com")

        assert result.response_time is not None
        assert isinstance(result.response_time, float)
        assert result.response_time >= 0


@pytest.mark.asyncio
async def test_single_redirect_successful(checker):
    """Проверяет корректную обработку одного редиректа."""
    original_url = "http://example.com"
    final_url = "http://final-example.com"

    mock_response_cm = AsyncMock()
    mock_response_cm.status = 200
    mock_response_cm.headers = {"content-type": "text/html"}
    mock_response_cm.url = final_url 
    mock_response_cm.__aenter__.return_value = mock_response_cm

    mock_get_method = AsyncMock(return_value=mock_response_cm)

    with patch("aiohttp.ClientSession.get", new=mock_get_method) as mock_get_call:
        result = await checker.check_url(original_url)

        assert result.is_available
        assert result.status == 200
        assert str(result.url).rstrip('/') == original_url.rstrip('/')
        assert str(result.final_url).rstrip('/') == final_url.rstrip('/')
        assert result.error is None
        mock_get_call.assert_called_once_with(
            original_url, 
            timeout=checker.timeout, 
            allow_redirects=True, 
            ssl=True, 
            max_redirects=checker.max_redirects_count
        )


@pytest.mark.asyncio
async def test_too_many_redirects(checker):
    """Проверяет обработку слишком большого количества редиректов."""
    original_url = "http://redirect-loop.com"
    
    checker.max_redirects_count = 1 # Устанавливаем малое значение для теста

    last_attempted_url = "http://redirect-loop.com/step1"
    exception_to_raise = aiohttp.TooManyRedirects(
        history=(), # type: ignore
        request_info=MagicMock(url=last_attempted_url, method='GET', headers=MagicMock()), # type: ignore
    )

    # Мок для метода session.get(), который сразу выбрасывает исключение при вызове
    exploding_get_method = AsyncMock(side_effect=exception_to_raise)
    
    with patch.object(checker._session, "get", new=exploding_get_method) as mock_get_call:
        result = await checker.check_url(original_url)

    assert not result.is_available
    assert result.status == 0
    assert "Too many redirects" in result.error 
    assert str(result.url).rstrip('/') == original_url.rstrip('/')
    assert result.final_url is None
    # Ошибка должна произойти на первой попытке, до того как retry-механизм (цикл) увеличит retry_count
    assert result.retry_count == 0 
    
    mock_get_call.assert_called_once_with(
        original_url, 
        timeout=checker.timeout, 
        allow_redirects=True, 
        ssl=True, 
        max_redirects=checker.max_redirects_count 
    )


@pytest.mark.asyncio
async def test_redirects_within_limit(checker):
    """Проверяет корректную обработку нескольких редиректов в пределах лимита."""
    original_url = "http://start.com"
    final_url = "http://final-destination.com"

    checker.max_redirects_count = 5 

    mock_response_cm = AsyncMock()
    mock_response_cm.status = 200 
    mock_response_cm.headers = {"content-type": "text/html"}
    mock_response_cm.url = final_url 
    mock_response_cm.__aenter__.return_value = mock_response_cm

    mock_get_method = AsyncMock(return_value=mock_response_cm)

    with patch("aiohttp.ClientSession.get", new=mock_get_method) as mock_get_call:
        result = await checker.check_url(original_url)

        assert result.is_available
        assert result.status == 200
        assert str(result.url).rstrip('/') == original_url.rstrip('/')
        assert str(result.final_url).rstrip('/') == final_url.rstrip('/')
        assert result.error is None
        assert result.retry_count == 0 # Редиректы не должны вызывать retry

        mock_get_call.assert_called_once_with(
            original_url, 
            timeout=checker.timeout, 
            allow_redirects=True, 
            ssl=True, 
            max_redirects=checker.max_redirects_count
        )
