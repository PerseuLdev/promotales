# 🧪 Guia de Testes - PromoTales Bot

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Configuração do Ambiente](#configuração-do-ambiente)
3. [Executando Testes](#executando-testes)
4. [Estrutura de Testes](#estrutura-de-testes)
5. [Cobertura de Código](#cobertura-de-código)
6. [Qualidade de Código](#qualidade-de-código)
7. [CI/CD](#cicd)
8. [Escrevendo Novos Testes](#escrevendo-novos-testes)
9. [Boas Práticas](#boas-práticas)

---

## 🎯 Visão Geral

O PromoTales Bot utiliza um framework de testes robusto para garantir qualidade e confiabilidade. Nossa estratégia de testes inclui:

- **Testes Unitários**: Validam componentes isolados
- **Testes de Integração**: Validam interação entre módulos
- **Cobertura Mínima**: 70% de code coverage
- **Qualidade de Código**: Black, Flake8, isort, MyPy
- **CI/CD**: GitHub Actions para automação

### 📊 Estatísticas Atuais

```
✅ Cobertura de Testes: 70%+
✅ Testes Unitários: 15+
✅ Testes de Integração: 5+
✅ Code Quality Score: A
```

---

## ⚙️ Configuração do Ambiente

### Pré-requisitos

```bash
# Python 3.8+
python --version

# Pip atualizado
pip install --upgrade pip
```

### Instalação de Dependências

```bash
# Instalar todas as dependências (incluindo testes)
pip install -r requirements.txt

# Ou usar o Makefile
make install
```

### Variáveis de Ambiente para Testes

Crie um arquivo `.env.test` (ou use `.env`):

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ENVIRONMENT=test
```

---

## 🏃 Executando Testes

### Usando Pytest Diretamente

```bash
# Executar todos os testes
pytest

# Executar com saída verbosa
pytest -v

# Executar testes específicos
pytest tests/test_bot.py
pytest tests/test_scraper.py::test_get_item_info

# Executar com cobertura
pytest --cov=src --cov-report=html

# Executar em paralelo (mais rápido)
pytest -n auto
```

### Usando Makefile (Recomendado)

```bash
# Executar todos os testes
make test

# Executar com cobertura
make test-cov

# Executar apenas testes unitários
make test-unit

# Executar apenas testes de integração
make test-integration

# Executar testes rápidos (sem slow tests)
make test-fast
```

### Marcadores (Markers)

```bash
# Executar apenas testes unitários
pytest -m unit

# Executar apenas testes de integração
pytest -m integration

# Excluir testes lentos
pytest -m "not slow"

# Executar apenas testes que não requerem Selenium
pytest -m "not selenium"
```

---

## 📁 Estrutura de Testes

```
tests/
├── __init__.py
├── conftest.py                 # Fixtures compartilhadas
├── test_bot.py                 # Testes do bot Telegram
├── test_scraper.py             # Testes do web scraper
├── test_config.py              # Testes de configuração
├── test_validators.py          # Testes de validadores
├── test_rate_limiter.py        # Testes de rate limiting
└── test_integration.py         # Testes de integração
```

### Fixtures Disponíveis (conftest.py)

```python
# Environment & Config
test_env_vars              # Variáveis de ambiente para testes
mock_settings              # Configurações mockadas

# Telegram Bot
mock_telegram_bot          # Bot Telegram mockado
mock_update                # Update mockado
mock_context               # CallbackContext mockado

# Web Scraper
mock_webdriver             # Selenium WebDriver mockado
mock_scraper_response      # Resposta do scraper mockada
sample_item_data           # Dados de item de exemplo

# Rate Limiter
mock_rate_limiter          # Rate limiter mockado

# Validators
valid_item_names           # Lista de nomes válidos
invalid_item_names         # Lista de nomes inválidos
```

---

## 📊 Cobertura de Código

### Gerando Relatório de Cobertura

```bash
# Gerar relatório HTML
pytest --cov=src --cov-report=html

# Abrir relatório no navegador
# O arquivo está em htmlcov/index.html

# Gerar relatório no terminal
pytest --cov=src --cov-report=term-missing

# Verificar se atinge 70% de cobertura
pytest --cov=src --cov-fail-under=70
```

### Configuração de Cobertura (pytest.ini)

```ini
[coverage:run]
source = src
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*

[coverage:report]
precision = 2
show_missing = True
skip_covered = False
```

### Visualizando Cobertura

```bash
# Usando Makefile
make test-cov

# Abrir relatório HTML
open htmlcov/index.html       # macOS
xdg-open htmlcov/index.html   # Linux
start htmlcov/index.html      # Windows
```

---

## 🎨 Qualidade de Código

### Black (Formatação)

```bash
# Formatar código
black src/ tests/

# Verificar sem modificar
black --check src/ tests/

# Usando Makefile
make format
make format-check
```

### Flake8 (Linting)

```bash
# Executar linting
flake8 src/ tests/

# Com estatísticas
flake8 src/ tests/ --count --show-source --statistics

# Usando Makefile
make lint
```

### isort (Ordenação de Imports)

```bash
# Ordenar imports
isort src/ tests/

# Verificar sem modificar
isort --check-only src/ tests/

# Fazer parte do make format
make format
```

### MyPy (Type Checking)

```bash
# Executar type checking
mypy src/ --ignore-missing-imports

# Usando Makefile
make type-check
```

### Executar Todas as Verificações

```bash
# Usando Makefile
make quality

# Ou manualmente
make format-check && make lint && make type-check
```

---

## 🔄 CI/CD

### GitHub Actions Workflow

O projeto possui um workflow completo de CI/CD em `.github/workflows/ci.yml`:

```yaml
jobs:
  quality:      # Code quality checks
  test:         # Unit & integration tests
  security:     # Security scanning
  build:        # Build verification
```

### Jobs do CI/CD

#### 1. Quality (Code Quality)
- Black formatting check
- isort import sorting
- Flake8 linting
- MyPy type checking

#### 2. Test (Tests)
- Executa em Python 3.8, 3.9, 3.10, 3.11
- Instala Chrome e ChromeDriver
- Roda pytest com cobertura
- Upload para Codecov

#### 3. Security (Security Scan)
- Safety check (dependency vulnerabilities)
- Bandit (security linter)

#### 4. Build (Build Check)
- Verifica import dos módulos principais
- Confirma que o projeto está buildável

### Executar CI Localmente

```bash
# Executar pipeline completo
make ci

# Ou passo a passo
make quality
make test-cov
```

### Badges do README

```markdown
![CI](https://github.com/seu-usuario/PromoTales/workflows/CI%2FCD%20Pipeline/badge.svg)
![Coverage](https://codecov.io/gh/seu-usuario/PromoTales/branch/main/graph/badge.svg)
```

---

## ✍️ Escrevendo Novos Testes

### Estrutura Básica de um Teste

```python
import pytest
from src.module import MyClass


@pytest.mark.unit
def test_my_function():
    """Test description."""
    # Arrange
    input_data = "test"
    expected = "expected_result"
    
    # Act
    result = my_function(input_data)
    
    # Assert
    assert result == expected
```

### Usando Fixtures

```python
@pytest.mark.unit
def test_with_fixture(mock_telegram_bot):
    """Test using a fixture."""
    # Fixture is automatically injected
    assert mock_telegram_bot.token is not None
    
    # Use the fixture
    result = mock_telegram_bot.get_me()
    assert result is not None
```

### Testando Funções Assíncronas

```python
import pytest


@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Testando Exceções

```python
import pytest


def test_exception():
    """Test that exception is raised."""
    with pytest.raises(ValueError):
        raise_error_function()
```

### Mockando Dependências

```python
from unittest.mock import Mock, patch


def test_with_mock():
    """Test using mocks."""
    # Create a mock
    mock_obj = Mock()
    mock_obj.method.return_value = "mocked_value"
    
    # Use the mock
    result = mock_obj.method()
    assert result == "mocked_value"
    
    # Verify mock was called
    mock_obj.method.assert_called_once()
```

### Parametrizando Testes

```python
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_multiple_inputs(input, expected):
    """Test with multiple input values."""
    result = my_function(input)
    assert result == expected
```

---

## 🏆 Boas Práticas

### 1. Nomeação de Testes

```python
# ✅ Bom
def test_get_item_info_returns_correct_price():
    pass

# ❌ Ruim
def test1():
    pass
```

### 2. Arrange-Act-Assert (AAA)

```python
def test_example():
    # Arrange: Preparar dados
    input_data = create_test_data()
    
    # Act: Executar ação
    result = function_under_test(input_data)
    
    # Assert: Verificar resultado
    assert result == expected_value
```

### 3. Um Assert por Teste (quando possível)

```python
# ✅ Bom
def test_price_is_positive():
    assert price > 0

def test_price_is_integer():
    assert isinstance(price, int)

# ❌ Ruim (múltiplos asserts não relacionados)
def test_price():
    assert price > 0
    assert isinstance(price, int)
    assert price < 1000000
```

### 4. Usar Fixtures para Setup Comum

```python
@pytest.fixture
def sample_item():
    return {"name": "Elmo", "price": 500000}

def test_price(sample_item):
    assert sample_item["price"] > 0

def test_name(sample_item):
    assert len(sample_item["name"]) > 0
```

### 5. Marcar Testes Adequadamente

```python
@pytest.mark.unit
def test_unit():
    pass

@pytest.mark.integration
def test_integration():
    pass

@pytest.mark.slow
def test_slow_operation():
    pass

@pytest.mark.selenium
def test_with_browser():
    pass
```

### 6. Isolar Testes

```python
# ✅ Bom: Cada teste é independente
def test_a():
    data = create_fresh_data()
    assert data.value == 1

def test_b():
    data = create_fresh_data()
    assert data.value == 1

# ❌ Ruim: Testes dependem de estado compartilhado
shared_data = None

def test_a():
    global shared_data
    shared_data = {"value": 1}

def test_b():
    assert shared_data["value"] == 1  # Falha se test_a não rodar
```

### 7. Testar Edge Cases

```python
def test_empty_string():
    assert validate("") == False

def test_none_value():
    assert validate(None) == False

def test_very_long_string():
    assert validate("a" * 10000) == False
```

---

## 📈 Métricas de Qualidade

### Objetivos

| Métrica | Meta | Atual |
|---------|------|-------|
| Cobertura de Código | ≥ 70% | 70%+ ✅ |
| Testes Unitários | ≥ 15 | 15+ ✅ |
| Testes de Integração | ≥ 5 | 5+ ✅ |
| Code Quality Score | A | A ✅ |
| Type Coverage | ≥ 50% | 50%+ ✅ |

---

## 🔧 Troubleshooting

### Testes Falhando Localmente

```bash
# Limpar cache
make clean

# Reinstalar dependências
pip install -r requirements.txt --force-reinstall

# Executar testes em modo verbose
pytest -vv
```

### ChromeDriver Issues

```bash
# Atualizar ChromeDriver automaticamente
pip install --upgrade chromedriver-autoinstaller

# Verificar versão do Chrome
google-chrome --version  # Linux
chrome --version         # macOS/Windows
```

### Problemas de Import

```python
# Adicionar ao início do arquivo de teste
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
```

---

## 📚 Recursos Adicionais

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Black Code Style](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [MyPy Documentation](https://mypy.readthedocs.io/)

---

**Última atualização:** 24 de Janeiro de 2026 (Milestone 3)  
**Versão:** 1.0  
**Responsável:** Equipe PromoTales
