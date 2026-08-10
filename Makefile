SHELL := /bin/bash
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:

PYTHON := python3
XCODE_DEVELOPER_DIR ?= /Applications/Xcode.app/Contents/Developer
DEVELOPER_DIR ?= $(XCODE_DEVELOPER_DIR)
export DEVELOPER_DIR
export PYTHONPATH := $(CURDIR)
export PYTHONDONTWRITEBYTECODE := 1
export COMPOSE_PROJECT_NAME := revenuecat-shipaton-2026
DEV_ROOT := $(CURDIR)/.dev
DEV_CACHE_DIR := $(DEV_ROOT)/cache
DEV_TMP_DIR := $(DEV_ROOT)/tmp
DEV_LOG_DIR := $(DEV_ROOT)/logs
override NPM_CONFIG_CACHE := $(DEV_CACHE_DIR)/npm
override npm_config_cache := $(NPM_CONFIG_CACHE)
override TMPDIR := $(DEV_TMP_DIR)
override PLAYWRIGHT_BROWSERS_PATH := $(DEV_CACHE_DIR)/ms-playwright
export NPM_CONFIG_CACHE
export npm_config_cache
export TMPDIR
export PLAYWRIGHT_BROWSERS_PATH
CLEAN_VERIFY_TIMEOUT_SECONDS ?= 1800
DEV_HEALTH_TIMEOUT_SECONDS ?= 30

SWIFT := xcrun swift
SWIFT_FORMAT := xcrun swift-format

.PHONY: help workspace-init locked-install verify-node-install install-e2e-browser \
	bootstrap check build test test-tools test-python lint format format-check \
	typecheck test-integration test-e2e eval run-local verify-all full-verify \
	release-check verify-clean policy-check dependency-audit sbom \
	dev\:preflight dev\:up dev\:down dev\:health

help:
	@printf '%s\n' \
	  'bootstrap         validate toolchains and install locked development dependencies' \
	  'check             format-check, lint, policy, and type-check' \
	  'build             compile the Swift package in release mode' \
	  'test              deterministic Swift and Python unit/property tests' \
	  'test-integration  exercise all four real loopback development services' \
	  'test-e2e          own all four services and browser-test the pattern outcome on 4222' \
	  'eval              run the current deterministic compatibility-evidence oracle' \
	  'verify-all        canonical complete local verification contract' \
	  'verify-clean      run verify-all from a detached clean checkout of HEAD' \
	  'release-check     alias of the canonical verification contract' \
	  'dev:preflight     validate exclusive ports and repository-local namespaces' \
	  'dev:up            start only this repository services on 127.0.0.1:4220-4223' \
	  'dev:health        verify semantic readiness for every allocated service' \
	  'dev:down          stop only ownership-validated recorded PIDs'

workspace-init:
	@$(PYTHON) tools/init_workspace.py

locked-install: workspace-init
	npm ci --ignore-scripts --no-audit --no-fund
	@npm ls --all --json >/dev/null
	@printf '%s\n' 'locked-install:ok source=package-lock.json scripts=disabled cache=repository-local'

verify-node-install: workspace-init
	@npm ls --all --json >/dev/null
	@test -x node_modules/.bin/playwright
	@printf '%s\n' 'node-install:ok dependency-tree=valid local-playwright=present'

install-e2e-browser: workspace-init verify-node-install
	@./node_modules/.bin/playwright install chromium

bootstrap: workspace-init
	@$(PYTHON) tools/bootstrap.py
	@$(MAKE) --no-print-directory locked-install
	@npm audit --audit-level=high

format: workspace-init
	@$(SWIFT_FORMAT) format --recursive --in-place Sources Tests/FoundationPropertyTests Package.swift

format-check: workspace-init
	@$(SWIFT_FORMAT) lint --recursive --strict Sources Tests/FoundationPropertyTests Package.swift
	@$(PYTHON) tools/check_text.py

policy-check: workspace-init
	@$(PYTHON) tools/check_policy.py

lint: format-check policy-check
	@$(PYTHON) -m compileall -q -f scripts tools Tests/python
	@printf '%s\n' 'lint:ok python-bytecode=valid swift-format=strict policy=valid'

typecheck: workspace-init
	@$(SWIFT) build --configuration debug
	@printf '%s\n' 'typecheck:ok swift-language-mode=6 strict-concurrency=complete'

check: format-check lint typecheck
	@printf '%s\n' 'check:ok'

build: workspace-init
	@$(SWIFT) build --configuration release
	@printf '%s\n' 'build:ok scope=portable-domain-package (not iOS/device/production evidence)'

test-tools: workspace-init
	@$(PYTHON) -m unittest discover -s tools/tests -p 'test_*.py' -v

test-python: workspace-init
	@$(PYTHON) -m unittest discover -s Tests/python -p 'test_*.py' -v

test: test-tools test-python
	@$(SWIFT) test --parallel
	@printf '%s\n' 'test:ok scope=deterministic-domain-and-repository-contract'

dev\:preflight: workspace-init
	@$(PYTHON) scripts/devctl.py preflight

dev\:up: workspace-init
	@$(PYTHON) scripts/devctl.py up --timeout "$(DEV_HEALTH_TIMEOUT_SECONDS)"

dev\:health: workspace-init
	@$(PYTHON) scripts/devctl.py health --timeout "$(DEV_HEALTH_TIMEOUT_SECONDS)"

dev\:down: workspace-init
	@$(PYTHON) scripts/devctl.py down

test-integration: workspace-init
	@set -euo pipefail; \
	  $(PYTHON) scripts/devctl.py down >/dev/null; \
	  trap '$(PYTHON) scripts/devctl.py down >/dev/null || true' EXIT; \
	  $(PYTHON) scripts/devctl.py preflight; \
	  $(PYTHON) scripts/devctl.py up --timeout "$(DEV_HEALTH_TIMEOUT_SECONDS)"; \
	  $(PYTHON) scripts/devctl.py health --timeout "$(DEV_HEALTH_TIMEOUT_SECONDS)"; \
	  $(PYTHON) tools/probe_services.py

test-e2e: workspace-init install-e2e-browser
	@set -euo pipefail; \
	  $(PYTHON) scripts/devctl.py down >/dev/null; \
	  trap '$(PYTHON) scripts/devctl.py down >/dev/null || true' EXIT; \
	  $(PYTHON) scripts/devctl.py preflight; \
	  env -u NO_COLOR npm run test:e2e

eval: workspace-init
	@$(SWIFT) test --filter EvaluationEvidencePropertyTests
	@printf '%s\n' 'eval:ok scope=typed-compatibility-evidence-policy (no physical results claimed)'

dependency-audit: workspace-init verify-node-install
	@npm audit --audit-level=high
	@$(SWIFT) package show-dependencies --format json >/dev/null
	@printf '%s\n' 'dependency-audit:ok npm=audited swift-graph=resolved'

sbom: workspace-init verify-node-install
	@mkdir -p .dev/artifacts
	@npm sbom --sbom-format cyclonedx > .dev/artifacts/development-sbom.cdx.json
	@$(SWIFT) package show-dependencies --format json > .dev/artifacts/swift-dependencies.json
	@$(PYTHON) -c 'import json; p=json.load(open(".dev/artifacts/development-sbom.cdx.json")); assert p["bomFormat"] == "CycloneDX" and len(p.get("components", [])) >= 1'
	@printf '%s\n' 'sbom:ok path=.dev/artifacts/development-sbom.cdx.json scope=development-harness'

verify-all: workspace-init
	@set -euo pipefail; \
	  before=.dev/tmp/verify-state-before.json; \
	  after=.dev/tmp/verify-state-after.json; \
	  $(PYTHON) tools/repository_state.py capture --output "$$before"; \
	  before_sha=$$(shasum -a 256 "$$before" | awk '{print $$1}'); \
	  trap '$(PYTHON) scripts/devctl.py down >/dev/null || true' EXIT; \
	  $(MAKE) --no-print-directory bootstrap; \
	  $(PYTHON) scripts/devctl.py preflight; \
	  $(PYTHON) scripts/devctl.py up --timeout "$(DEV_HEALTH_TIMEOUT_SECONDS)"; \
	  $(PYTHON) scripts/devctl.py health --timeout "$(DEV_HEALTH_TIMEOUT_SECONDS)"; \
	  $(MAKE) --no-print-directory format-check; \
	  $(MAKE) --no-print-directory lint; \
	  $(MAKE) --no-print-directory typecheck; \
	  $(MAKE) --no-print-directory build; \
	  $(MAKE) --no-print-directory test; \
	  $(MAKE) --no-print-directory test-integration; \
	  $(MAKE) --no-print-directory test-e2e; \
	  $(MAKE) --no-print-directory eval; \
	  $(MAKE) --no-print-directory dependency-audit; \
	  $(MAKE) --no-print-directory sbom; \
	  $(PYTHON) scripts/devctl.py down; \
	  test "$$before_sha" = "$$(shasum -a 256 "$$before" | awk '{print $$1}')" || { printf '%s\n' 'verify-all:error baseline-snapshot=modified'; exit 1; }; \
	  $(PYTHON) tools/repository_state.py compare --before "$$before" --after "$$after"; \
	  printf '%s\n' 'verify-all:ok dependency-install=lock-derived tracked-content=stable index=stable untracked-content=stable ignored-artifacts=allowlisted services=ownership-stopped'

full-verify: verify-all

release-check: verify-all

verify-clean: workspace-init
	@$(PYTHON) scripts/devctl.py down
	@$(PYTHON) tools/verify_clean_checkout.py --timeout-seconds "$(CLEAN_VERIFY_TIMEOUT_SECONDS)"

run-local: dev\:up dev\:health
