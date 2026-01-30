.PHONY: help install test test-cov lint format type-check quality clean run all

# Default target
help:
	@echo "PromoTales Bot - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       - Install all dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-cov      - Run tests with coverage report"
	@echo "  make test-unit     - Run only unit tests"
	@echo "  make test-integration - Run only integration tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run flake8 linting"
	@echo "  make format        - Format code with black and isort"
	@echo "  make format-check  - Check code formatting without changes"
	@echo "  make type-check    - Run mypy type checking"
	@echo "  make quality       - Run all quality checks"
	@echo ""
	@echo "Application:"
	@echo "  make run           - Run the bot"
	@echo "  make clean         - Clean up cache and build files"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci            - Run full CI pipeline locally"
	@echo ""

# ============================================================================
# Setup
# ============================================================================

install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "✅ Dependencies installed successfully!"

# ============================================================================
# Testing
# ============================================================================

test:
	@echo "Running tests..."
	pytest -v tests/

test-cov:
	@echo "Running tests with coverage..."
	pytest -v --cov=src --cov-report=html --cov-report=term-missing tests/
	@echo "✅ Coverage report generated in htmlcov/index.html"

test-unit:
	@echo "Running unit tests..."
	pytest -v -m unit tests/

test-integration:
	@echo "Running integration tests..."
	pytest -v -m integration tests/

test-fast:
	@echo "Running fast tests (excluding slow tests)..."
	pytest -v -m "not slow" tests/

# ============================================================================
# Code Quality
# ============================================================================

lint:
	@echo "Running flake8..."
	flake8 src/ tests/ --count --show-source --statistics

format:
	@echo "Formatting code with black..."
	black src/ tests/
	@echo "Sorting imports with isort..."
	isort src/ tests/
	@echo "✅ Code formatted successfully!"

format-check:
	@echo "Checking code formatting..."
	black --check src/ tests/
	isort --check-only src/ tests/

type-check:
	@echo "Running mypy type checking..."
	mypy src/ --ignore-missing-imports

quality: format-check lint type-check
	@echo "✅ All quality checks passed!"

# ============================================================================
# Application
# ============================================================================

run:
	@echo "Starting PromoTales Bot..."
	python main_new.py

run-old:
	@echo "Starting PromoTales Bot (old version)..."
	python main.py

# ============================================================================
# CI/CD
# ============================================================================

ci: quality test-cov
	@echo "✅ CI pipeline completed successfully!"

# ============================================================================
# Cleanup
# ============================================================================

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed!"

# ============================================================================
# All-in-one
# ============================================================================

all: clean install quality test-cov
	@echo "✅ Full build and test completed successfully!"
