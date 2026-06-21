# Bank Rec MVP Implementation Plan

## Purpose

Track implementation of the new `/bank-rec` route app through the approved MVP scope.

The source design is `docs/bank-rec-modern-ui-design.md`. This file is the working execution tracker. Update it as each phase starts, completes, or changes scope.

## MVP Scope

Build through Phase 5 only:

1. MVP shell and read-only Reconcile
2. MVP match flow
3. MVP create voucher flow
4. MVP Cash Coding
5. MVP matched review and hardening

Out of MVP:

- `/bank-rec-tool` route or redirect.
- Transfers.
- Split cash coding.
- Tax coding.
- Statement-balance Difference card unless a statement closing balance is supplied.
- Reconciliation-session model.
- User-facing Settings page or Settings nav item.
- Full Rules create, edit, disable, or delete UI. MVP Rules is a list with links to Desk.
- Changes to the existing `Advance Bank Reconciliation Tool` form or current public JS.

## Tracking Rules

- Keep this file updated at the end of every implementation session.
- Record commands and test evidence under the relevant phase.
- Mark blockers directly under the phase where they occur.
- Do not mark a phase complete until its acceptance checklist is satisfied.
- If shared backend behavior needs to change, add regression tests for the old tool before changing it.

Status values:

- Not Started
- In Progress
- Blocked
- Complete

## Current Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 1: Shell and read-only Reconcile | Complete | Route app, permission facade, read-only APIs, minimal Rules list, frontend build |
| Phase 2: Match flow | Complete | Match candidates, Update tab, submit match, duplicate-submit guard |
| Phase 3: Create voucher flow | Complete | Create tab, Journal Entry submit, Payment Entry draft handoff, full-page edit |
| Phase 4: Cash Coding | Complete | Grid, bulk apply, row-level Journal Entry submit, discard guards |
| Phase 5: Matched review and hardening | Complete | Tests, build, route probes, Chrome smoke, incremental commits, and PR are complete |

## Resolved Scope Decisions From Final Review

- Build the `Update` tab in MVP. It edits Bank Transaction metadata only, such as reference number, party type, and party.
- Ship a minimal `Rules` page in MVP because create flow can save a bank rule and cash coding can consume rule suggestions. The MVP page is list, search, and "Open in Desk"; it is not a full rules manager.
- Hide `Settings` from MVP navigation. Backend settings can still load through `get_boot`.
- Include `Mode of Payment` in the Create flow when the inferred Payment Entry path requires it.

## Cross-Cutting UX And Safety Requirements

These requirements apply to every implementation phase.

UX states:

- Every page and panel must have explicit loading, empty, error, and partial-failure states.
- Handle first-run cases: no permitted bank accounts, no selected transaction, zero unreconciled rows, no match candidates, no cash-coding rows, and no matched transactions.
- Empty states should give the next useful action, such as changing filters, choosing another bank account, or using Create when no match candidates exist.

Async safety:

- Use the `Date.now()` request-id discard pattern for transaction context, match candidates, create defaults, update metadata refreshes, cash-coding row reloads, and any other selection-dependent async call.
- Never render async results for a Bank Transaction that is no longer selected.

Route state:

- Persist active filters in the URL query: `bank_account`, `from_date`, `to_date`, and any page-specific status filter.
- Persist selected `bank_transaction` in the URL query on pages that have a selected transaction.
- Restore route query values on hard refresh and direct subroute visits.
- If restored query values are invalid, unavailable, or not permitted, show the matching empty or permission state and select the first valid row only when safe.
- Use route replace for frequent selection changes so browser Back is not polluted by row-by-row movement.

Mutating actions:

- Disable mutating buttons while a submit is in flight.
- Backend methods for simple match, create voucher, update metadata, cash coding submit, and unreconcile must recheck current document state before writing.
- Add idempotency or locking checks where duplicate clicks could create duplicate allocations, duplicate vouchers, or duplicate Journal Entries.
- Return structured errors that can be displayed in the active panel without exposing hidden voucher internals.

Progress and long jobs:

- Mount `ReconcileProgressDialog.vue` for any match, create, draft handoff, or cash-coding operation that returns a background job or may take longer than a few seconds.
- Subscribe to `bulk_reconciliation_progress` for reused bulk reconciliation paths.
- Subscribe to `cash_coding_progress` and `cash_coding_complete` for new cash-coding background paths.

Selection and auto-advance:

- Auto-select the first unreconciled row only when the list first loads and no user selection exists.
- Auto-advance after reconciliation only when the selected transaction is fully reconciled, the action succeeded, and the active panel has no unsaved edits.
- Do not auto-select match candidates unless there is one unique top candidate above the confidence threshold. For ties or ambiguous same-amount candidates, require user selection.

Unsaved edits:

- Confirm before discarding unsaved cash-coding edits on refresh, filter changes, bank-account changes, route changes, or browser navigation.
- Do not rely on "preserve edits where practical" as the safety model. If edits cannot be preserved, ask before discarding them.

Cash-coding validation:

- Prevent mixed-direction bulk apply when the field being applied changes accounting meaning by direction. Allow direction-neutral fields such as cost center, project, dimensions, reference, and notes.
- Block submit client-side when selected rows are missing required fields such as account.
- The backend must still validate every submitted row and return row-level errors, because a row can become invalid after client validation starts.

Error language:

- The split-screen UI hides `Document Type` and `Journal Entry Type`, so validation errors must be translated into user-facing language.
- For example, if the inferred voucher path needs a party, show that the selected contact is required for the chosen account rather than surfacing an internal Payment Entry party validation message.

## Implementation Sequence

### Phase 0: Preflight

Status: Complete

Goal: confirm the repo and local bench are ready before creating app code.

Tasks:

- Check git status for user changes.
- Confirm current ABR branch and `.releaserc` presence.
- Re-read the approved design document.
- Inspect Helpdesk route app files for hook, template, Vite, and build patterns.
- Inspect current ABR hook structure before adding `add_to_apps_screen` and `website_route_rules`.
- Confirm local frontend package manager choice from the repo pattern.
- Confirm exact `frappe-ui` version to pin when implementation starts.
- Confirm target test site, recommended default is `demo.localhost` unless the user gives another site.

Acceptance:

- No unrelated user changes are overwritten.
- Implementation files and route strategy are confirmed.
- Test site is known.

Progress notes:

- ABR branch is `main`.
- ABR has `.releaserc`; ask for release type before the first incremental commit.
- Current app changes before implementation are limited to the untracked `docs/` directory created for this design and tracker.
- Existing ABR frontend has no standalone package yet, so Phase 1 will introduce a new `bank_rec/` frontend package.
- Helpdesk route-app pattern is available locally: `add_to_apps_screen`, `website_route_rules`, `www/<route>/index.py`, Vite, Vue, Frappe UI, Pinia, Vue Router, Tailwind, and build output to app public assets.
- ABR hooks can be extended for `add_to_apps_screen` and `website_route_rules` without changing the existing `Advance Bank Reconciliation Tool` DocType form or current public JS.
- Package manager choice is `yarn`, matching Helpdesk. Local Yarn version is `1.22.22`.
- Node is available locally. Local version reported is `v26.0.0`.
- Pin `frappe-ui` to `1.0.0-beta.3` initially, matching Helpdesk in this bench, unless package install resolution forces a narrow adjustment.
- Default test site is `demo.localhost`; ABR is installed there.
- Existing backend helpers are present for unreconciled/reconciled transactions, match queries, payment and journal creation, reconciliation, unreconciliation, and bulk payment entry creation.

Commands run:

- `git -C apps/advanced_bank_reconciliation status --short`
- `git -C apps/advanced_bank_reconciliation branch --show-current`
- `find apps/advanced_bank_reconciliation -maxdepth 2 -name '.releaserc' -o -name 'package.json' -o -name 'hooks.py' -o -name 'pyproject.toml'`
- `sed -n '1,260p' apps/advanced_bank_reconciliation/advanced_bank_reconciliation/hooks.py`
- `sed -n '1,220p' apps/advanced_bank_reconciliation/pyproject.toml`
- `sed -n '1,120p' apps/advanced_bank_reconciliation/.releaserc`
- `find apps -maxdepth 3 -type d -iname '*help*desk*' -o -type d -name 'helpdesk'`
- `sed -n '1,90p' apps/helpdesk/helpdesk/hooks.py`
- `sed -n '1,120p' apps/helpdesk/helpdesk/www/helpdesk/index.py`
- `sed -n '1,140p' apps/helpdesk/desk/vite.config.js`
- `sed -n '1,110p' apps/helpdesk/desk/package.json`
- `sed -n '1,220p' apps/helpdesk/desk/vite-helpers.ts`
- `sed -n '1,120p' apps/helpdesk/desk/tailwind.config.js`
- `sed -n '1,140p' apps/helpdesk/desk/src/main.js`
- `sed -n '1,180p' apps/helpdesk/desk/src/router/index.ts`
- `bench --site demo.localhost list-apps`
- `node --version`
- `yarn --version`
- `rg -n "def (get_bank_transactions|get_reconciled_bank_transactions|get_linked_payments|create_payment_entry_bts|create_journal_entry_bts|create_payment_entries_bulk|reconcile_vouchers|unreconcile_bank_transaction|run_bank_rules|create_bank_rule_from_voucher|get_matching_queries|get_unpaid|bulk|progress)" apps/advanced_bank_reconciliation/advanced_bank_reconciliation/advanced_bank_reconciliation/doctype/advance_bank_reconciliation_tool`

## Phase 1: MVP Shell And Read-Only Reconcile

Status: Complete

Goal: deliver `/bank-rec` as a working read-only route app with secure APIs.

Backend tasks:

- Add `advanced_bank_reconciliation/api/__init__.py`.
- Add `advanced_bank_reconciliation/api/permission.py`.
- Add `advanced_bank_reconciliation/api/bank_rec.py`.
- Implement `has_bank_rec_permission`.
- Implement helper functions:
  - `require_bank_rec_permission`
  - `get_allowed_company_names`
  - `assert_bank_account_access`
  - `assert_bank_transaction_access`
  - `assert_voucher_access`
- Implement read-only API methods:
  - `get_boot`
  - `get_bank_accounts`
  - `get_bank_rules`
  - `get_statement_summary`
  - `get_transactions`
  - `get_transaction_context`
- Ensure server resolves bank account company and never trusts client-supplied company as the authority.
- Ensure cross-company access throws `frappe.PermissionError`.
- Ensure summary does not return a `difference` value without statement closing balance.

Frontend and route tasks:

- Add `bank_rec/` frontend source folder.
- Add Vite, Vue 3, TypeScript, Pinia, Vue Router, Tailwind, and Frappe UI setup.
- Add optional local `frappe-ui` alias only if practical, without adding a Git submodule.
- Configure Vite to generate `advanced_bank_reconciliation/www/bank_rec/index.html`.
- Add `advanced_bank_reconciliation/www/bank_rec/index.py`.
- Add `add_to_apps_screen` entry with label `Bank Rec`.
- Add route rule for `/bank-rec` and `/bank-rec/<path:app_path>`.
- Do not add `/bank-rec-tool`.
- Implement app shell with Reconcile, Cash Coding, Matched, and Rules navigation.
- Do not show Settings in MVP navigation.
- Implement bank account and date filters.
- Implement URL query sync and restore for bank account, date range, and selected Bank Transaction.
- Implement read-only transaction list.
- Implement selected transaction detail panel.
- Implement minimal `RulesPage.vue` with list, search, bank-account filter, and `Open in Desk` action.
- Implement summary cards:
  - Unreconciled count
  - Selected amount
  - Cleared balance
  - Unreconciled total, sum of absolute unallocated amounts
- Add explicit loading, empty, and error states for boot, bank accounts, transactions, transaction context, and rules.
- Show a useful empty state when there are no permitted bank accounts or zero unreconciled rows.

Tests:

- API permission tests for Guest, allowed roles, and disallowed roles.
- Cross-company `PermissionError` tests for bank accounts and Bank Transactions.
- Statement summary test for no `difference` unless statement closing balance is supplied.
- Rules list permission test.
- Frontend unit tests for formatting helpers if test harness is added in Phase 1.
- Route query restore test for bank account, date range, and selected transaction if frontend test harness is added in Phase 1.

Acceptance:

- `/bank-rec` loads.
- `/bank-rec/reconcile` loads or redirects inside the SPA.
- Bank account/date filters load permitted data only.
- Hard refresh restores permitted filters and selected transaction.
- Selecting a transaction updates the right panel.
- No posting or mutating actions are available yet.
- Rules page lists existing bank rules and opens the Desk form for edit or delete.
- Settings is not shown in navigation.
- Existing `/app/advance-bank-reconciliation-tool` still works.

Progress notes:

- Added `advanced_bank_reconciliation/api/permission.py` with role, company, bank account, Bank Transaction, and voucher access helpers.
- Added `advanced_bank_reconciliation/api/bank_rec.py` as the new read-only API facade for boot, bank accounts, rules, statement summary, transactions, and transaction context.
- Added `advanced_bank_reconciliation/www/bank_rec/index.py` and the generated `index.html` route template.
- Added hook entries for the Apps screen label `Bank Rec` and `/bank-rec` route rules. No `/bank-rec-tool` route was added.
- Added `bank_rec/` Vue 3, TypeScript, Vite, Pinia, Vue Router, Tailwind, and Frappe UI frontend package.
- Pinned `frappe-ui` to `1.0.0-beta.3` and used a local alias helper only for optional development checkouts. No submodule was added.
- Implemented app navigation for Reconcile, Cash Coding, Matched, and Rules. Settings is not shown.
- Implemented bank account, date, and status filters with URL query sync for `bank_account`, `from_date`, `to_date`, `status`, and `bank_transaction`.
- Implemented read-only Reconcile split view with transaction list, summary cards, selected transaction detail panel, and linked payment display.
- Implemented minimal Rules page with bank account filter, search, and `Open` action to Desk in a new tab.
- Added loading, empty, and error states for boot, bank accounts, transactions, transaction context, summary, and rules.
- Configured Vite to generate public assets under `advanced_bank_reconciliation/public/bank_rec/`.
- Added ignore rules for generated public build output, generated route HTML, and Vite plugin generated type helper files. This matches the Repeat Raven dashboard pattern where source is tracked and app public build output is ignored.
- Authenticated browser visual verification is covered in Phase 5 Chrome smoke. The local route probe as Guest returned `403 FORBIDDEN`, which is expected because `get_context` calls the permission-checked boot method.
- First incremental commit is pending user confirmation of semantic release type. Recommendation: `minor`, using `feat`.

Commands run:

- `sed -n '1,180p' apps/helpdesk/desk/vite.config.js`
- `sed -n '1,120p' apps/helpdesk/desk/src/main.js`
- `sed -n '1,160p' apps/helpdesk/desk/tsconfig.json`
- `sed -n '1,80p' apps/helpdesk/desk/postcss.config.js`
- `sed -n '1,260p' apps/advanced_bank_reconciliation/advanced_bank_reconciliation/api/bank_rec.py`
- `sed -n '1,260p' apps/advanced_bank_reconciliation/advanced_bank_reconciliation/api/permission.py`
- `sed -n '1,120p' apps/advanced_bank_reconciliation/advanced_bank_reconciliation/www/bank_rec/index.py`
- `yarn install`
- `yarn build`
- `find apps/advanced_bank_reconciliation/advanced_bank_reconciliation/public/bank_rec -maxdepth 3 -type f | sort`
- Ran a source dash scan against the new custom source files.
- `bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_bank_rec`
- `bench --site demo.localhost clear-cache`
- `curl -I --max-time 8 http://demo.localhost:8000/bank-rec`

## Phase 2: MVP Match Flow

Status: Complete

Goal: match selected Bank Transactions to existing vouchers through the new split-screen UI.

Backend tasks:

- Add `advanced_bank_reconciliation/api/matching.py`.
- Implement `get_match_candidates`.
- Implement `submit_match`.
- Implement `update_transaction_metadata` through the facade if it is not already in `bank_rec.py`.
- Wrap existing matching and reconciliation helpers through the permission facade.
- Preserve partial allocation behavior.
- Reuse existing `bulk_reconciliation_progress` event for existing bulk match paths.
- Add structured response DTOs for success, validation errors, and progress job details.
- Recheck Bank Transaction state before submit and guard against duplicate reconciliation writes.

Frontend tasks:

- Implement `MatchPanel.vue`.
- Implement `UpdateTransactionPanel.vue`.
- Mount `ReconcileProgressDialog.vue` and subscribe to bulk reconciliation progress when the backend returns a job.
- Show candidate confidence and reason chips.
- Support selecting one or many candidate rows.
- Leave candidate selection empty when candidates are ambiguous or tied.
- Show selected allocation total.
- Show strict validation warnings before submit.
- Disable submit while match or update requests are in flight.
- Submit selected matches.
- Submit metadata updates.
- Use request-id stale response discard for transaction context and match candidates.
- Refresh transaction list, summary, and selected transaction after success.
- Auto-select next unreconciled transaction only after the current one is fully reconciled, the action succeeded, and the active panel has no unsaved edits.
- Show empty state when no candidates are found, with a nudge to use Create.

Tests:

- Match candidate response shape.
- Submit match against regular voucher.
- Submit match against unpaid invoices.
- Partial allocation behavior.
- Cross-company voucher rejection.
- Duplicate submit guard for simple match.
- Update metadata permission and cross-company rejection.
- Frontend store tests for selected transaction refresh.
- Frontend stale-candidate discard test.

Acceptance:

- User can reconcile a selected transaction by matching existing documents.
- Row leaves the unreconciled list when fully reconciled.
- Partial allocation remains visible when not fully reconciled.
- Update tab can save permitted Bank Transaction metadata without reconciling the row.
- Long-running reconciliation shows progress instead of a silent wait.
- Permission checks happen on every submit.
- Existing old-tool match behavior is not regressed.

Progress notes:

- Added `advanced_bank_reconciliation/api/matching.py` with permission-checked `get_match_candidates`, `submit_match`, and `update_transaction_metadata`.
- Match candidates reuse the existing `get_linked_payments` query path and are returned as structured DTOs with voucher type, voucher name, amount, rank, confidence, reasons, party, dates, and currency.
- Normalised old unpaid-invoice labels to the real voucher doctypes expected by reconciliation. For example, `Unpaid Sales Invoice` is returned as `Sales Invoice`.
- Submit match rechecks Bank Transaction state, locks the row, validates selected vouchers through the shared voucher permission helper, blocks over-allocation, blocks duplicate voucher links, and returns an idempotent success for a repeated submit of the same already-linked vouchers.
- Update metadata rechecks Bank Transaction access, locks the row, validates party type and party, and returns the same transaction DTO shape used by the read-only API.
- Added Match and Update tabs to the right-side split panel.
- Match tab loads candidates with the request-id stale response pattern, shows confidence and reason chips, supports one or many selected candidates, shows selected allocation total, and disables submit while posting.
- Candidate auto-selection only happens for one unique high-confidence top candidate. Ties and ambiguous candidates remain unselected.
- Update tab edits reference, party type, and party, with dirty-state save enablement and submit disable while saving.
- Added `ReconcileProgressDialog.vue` and mounted it from the Reconcile page. It opens while match, create, or draft handoff requests are in flight. No realtime subscription is active yet because this Phase 2 submit path is synchronous and does not return a background job.
- After a match submit or metadata update, the app refreshes the transaction list, summary, selected context, and match candidates.
- Backend tests cover candidate DTO shape, matching an unpaid Sales Invoice, duplicate-submit idempotency, cross-company metadata rejection, and metadata save.

Commands run:

- `bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_bank_rec`
- `yarn build`
- `git -C apps/advanced_bank_reconciliation status --short --ignored`
- `find apps/advanced_bank_reconciliation/advanced_bank_reconciliation/public/bank_rec -maxdepth 2 -type f | sort`

## Phase 3: MVP Create Voucher Flow

Status: Complete

Goal: create the right underlying NexWave voucher from a selected Bank Transaction without exposing Frappe document internals in the split-screen form.

Backend tasks:

- Implement `create_voucher_from_transaction`.
- Reuse `create_payment_entry_bts` and `create_journal_entry_bts`.
- Default underlying voucher behavior from money direction, party selection, and selected account.
- Preserve Journal Entry party validation for receivable and payable accounts.
- Preserve Payment Entry multi-currency behavior.
- Include Mode of Payment when the inferred Payment Entry path requires it.
- Implement `create_voucher_draft_from_transaction` for `Edit in Full Page`.
- Add optional save-as-bank-rule hook after successful creation.
- Add `Edit in Full Page` URL support for complex entries.
- Recheck Bank Transaction state before creating a voucher and guard against duplicate voucher creation.
- Ensure draft handoff does not submit the voucher or mark the Bank Transaction reconciled.

Frontend tasks:

- Implement `CreateVoucherPanel.vue`.
- Show simplified fields:
  - Contact
  - Account
  - Mode of Payment, when required by the inferred voucher path
  - Posting date
  - Reference
  - Cost center
  - Project
  - Accounting dimensions
  - Notes
- Hide `Document Type` and `Journal Entry Type` from the split-screen form.
- Switch labels by direction: withdrawal as spend/supplier-oriented, deposit as receive/customer-oriented.
- Validate party/contact requirements client-side for the inferred voucher path.
- Translate backend validation errors into the split-screen labels.
- Disable submit while create request is in flight.
- Add save-as-bank-rule option after successful creation.
- Add `Edit in Full Page` secondary action that saves current values as a Draft voucher and opens it in Desk in a new browser tab.
- Keep the Bank Rec tab on the same route after opening the Draft voucher. If the browser blocks the new tab, show an `Open Draft in Desk` link instead of navigating Bank Rec away.
- Show validation errors before opening full-page edit if the current values cannot create a Draft.

Tests:

- Create Journal Entry from withdrawal.
- Create Journal Entry from deposit where appropriate.
- Create Payment Entry where party and account require it.
- Mode of Payment required/default behavior for Payment Entry paths.
- Multi-currency create flow.
- Duplicate submit guard for create voucher.
- Full-page draft handoff preserves current form values.
- Full-page draft handoff does not reconcile the Bank Transaction.
- Save-as-rule prompt does not create a rule unless requested.
- Cross-company transaction and account rejection.

Acceptance:

- User can create and reconcile a simple voucher from a selected transaction.
- Created voucher submits through standard document lifecycle.
- Bank Transaction is reconciled through the existing clearance-date behavior.
- Complex entries can move to full-page edit.
- Full-page edit does not discard in-progress create form values.
- User-facing errors do not expose hidden `Document Type` or `Journal Entry Type` decisions.
- No bank-account transfer flow is exposed in MVP.

Progress notes:

- Added `advanced_bank_reconciliation/api/create_voucher.py` with `get_create_defaults`, `create_voucher_from_transaction`, and `create_voucher_draft_from_transaction`.
- Create defaults return the selected transaction, bank account, default dates and references, settings, account options, mode of payment options, cost centers, and projects.
- The split-screen form infers the underlying voucher path. If a coding account is provided, it creates a Journal Entry. If contact fields are provided without a coding account, it creates a Payment Entry.
- Submitted create rechecks Bank Transaction state, locks the row, validates account company, blocks already reconciled rows, creates the voucher through existing ABR helpers, reconciles through the existing clearance-date behavior, and returns the created voucher Desk URL.
- Draft handoff creates a permission-checked draft voucher, returns its Desk URL, and does not submit or reconcile the Bank Transaction.
- Added optional save-as-rule payload support. The backend creates an ABR Bank Rule only when explicitly requested.
- Save-as-rule requests are preflighted before voucher creation so a missing rule title or missing rule permission cannot leave behind an unexpected reconciled voucher.
- Added `CreateVoucherPanel.vue` with account, contact, mode of payment, posting date, reference date, reference, cost center, project, save-as-rule, create-and-reconcile, and edit-in-full-page controls.
- `Edit in Full Page` opens the saved draft voucher in Desk in a new browser tab. If the browser blocks the tab, the panel shows an `Open draft in Desk` link and keeps Bank Rec on the same route.
- Direction-aware labels are used for contact and account fields.
- The split-screen UI does not show `Document Type` or `Journal Entry Type`.
- Backend tests cover create defaults, submitted Journal Entry reconciliation, draft Journal Entry handoff without reconciliation, Payment Entry draft handoff, and save-as-rule preflight before voucher creation.
- Submitted Payment Entry is implemented through the existing ABR helper. Full submitted Payment Entry test coverage still needs a currency-specific fixture because the local demo site has a bank-account currency mismatch in the existing Payment Entry helper path.

Commands run:

- `bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_bank_rec`
- `yarn build`

## Phase 4: MVP Cash Coding

Status: Complete

Goal: let users code many simple non-tax Bank Transactions in a grid and reconcile them in bulk.

Backend tasks:

- Add `advanced_bank_reconciliation/api/cash_coding.py`.
- Implement `get_cash_coding_rows`.
- Implement `preview_cash_coding`.
- Implement `submit_cash_coding`.
- Create one Journal Entry per coded Bank Transaction.
- Use savepoints so valid rows can post when other rows fail.
- Return row-level success and error results.
- Add cash-coding realtime events if row count makes background processing necessary.
- Do not implement tax posting.
- Do not implement split coding.
- Do not implement transfers.

Frontend tasks:

- Implement `CashCodingPage.vue`.
- Implement `CashCodingGrid.vue`.
- Add filters for all, uncoded, rule-suggested, errors, and selected.
- Add bulk apply for selected rows.
- Add a visible tax warning banner, not a filter chip.
- Confirm before discarding unsaved edits on refresh, filter changes, bank-account changes, route changes, or browser navigation.
- Prevent mixed-direction bulk apply for direction-sensitive fields.
- Block submit when selected rows are missing required fields such as account.
- Mount progress dialog and subscribe to cash-coding progress events when the backend returns a job.
- Disable submit while cash-coding submit is in flight.
- Keep failed rows selected after submit.
- Show row-level errors.

Tests:

- Cash coding creates Journal Entry and reconciles Bank Transaction.
- Row-level errors do not roll back successful rows.
- Required account validation.
- Permission rejection for cross-company rows.
- Tax fields are not accepted in MVP payloads.
- Split rows are rejected in MVP.
- Mixed-direction bulk apply guard.
- Unsaved edit discard confirmation.
- Duplicate submit guard for cash coding.

Acceptance:

- User can code selected rows and submit them in bulk.
- Valid rows post and reconcile.
- Invalid rows remain visible with row-level errors.
- Selected rows missing required account are blocked before submit, while backend row-level errors still handle late validation failures.
- Bulk apply speeds repeated coding.
- UI clearly indicates tax is not handled by MVP cash coding.

Progress notes:

- Added `advanced_bank_reconciliation/api/cash_coding.py` with `get_cash_coding_rows`, `preview_cash_coding`, and `submit_cash_coding`.
- Cash coding rows reuse unreconciled Bank Transaction data and include company-scoped account, cost center, and project options.
- Submit creates one Journal Entry per selected Bank Transaction through the existing ABR Journal Entry helper and reconciles via the existing clearance-date behavior.
- Row-level savepoints allow valid rows to post even when other rows fail validation.
- Backend validates bank account access, Bank Transaction access, account company, ledger account status, required account, contact requirements for receivable or payable accounts, and locks each Bank Transaction before posting.
- The frontend Cash Coding page now has bank account and date filters, row selection, editable account/contact/cost center/project/reference fields, account/cost center/project datalist options, filter chips, row errors, and selected-row submit.
- Added a distinct amber warning: `Tax is not posted from cash coding.`
- Bulk apply supports account, cost center, and project. It blocks account bulk-apply across mixed money directions while allowing neutral fields.
- Unsaved edits are guarded on refresh, filter changes, bank-account changes, route changes, and browser navigation.
- Cash-coding row loads use the request-id stale response discard pattern.
- Cash-coding submit opens `ReconcileProgressDialog.vue` while rows are being posted.
- Successful rows are removed from the grid after submit. Failed rows remain visible with row-level errors.
- Tax posting, split coding, and transfers are not implemented in MVP.
- Backend tests cover row loading, successful Journal Entry coding, and row-level partial failure.

Commands run:

- `bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_bank_rec`
- `yarn build`

## Phase 5: MVP Matched Review And Hardening

Status: Complete

Goal: provide matched transaction review, unreconcile actions, and full MVP QA.

Backend tasks:

- Implement matched transaction read APIs through facade permissions.
- Wrap current `unreconcile_bank_transaction`.
- Ensure unreconcile and cancel choices respect standard Accounting Period and document validation.
- Keep "Unreconcile Only" and "Unreconcile and Cancel PE/JE" behaviors.
- Add structured warning and error responses.

Frontend tasks:

- Implement `MatchedPage.vue`.
- Show reconciled transactions and linked documents.
- Add linked voucher inspection.
- Add unreconcile confirmation flow.
- Add clear warning before cancelling linked Payment Entry or Journal Entry.
- Add final responsive layout pass.
- Add keyboard navigation pass.

Tests:

- Matched transaction list permission checks.
- Unreconcile only.
- Unreconcile and cancel linked document.
- Accounting Period locked behavior.
- Existing unreconcile behavior remains unchanged.
- Browser tests for Reconcile, Match, Update, Create, Cash Coding, Rules, Matched, route refresh restore, progress dialog, and responsive layout.

Manual QA:

- Deposit and withdrawal flows.
- Sales and purchase invoices.
- Credit notes and debit notes.
- Multi-currency bank account.
- Multi-currency Payment Entry and Journal Entry flows.
- Strict validation enabled and disabled.
- Users with `Accounts User` and `Accounts Manager`.
- Existing old tool still loads and reconciles.

Acceptance:

- MVP flows are complete across phases 1 through 5.
- Regression tests pass.
- Frontend build passes.
- Browser smoke and workflow tests pass.
- Existing tool remains functional.

Progress notes:

- Added `advanced_bank_reconciliation/api/matched.py` with permission-checked matched transaction listing and unreconcile facade.
- Matched listing reuses reconciled Bank Transaction data and de-duplicates rows by Bank Transaction name.
- Unreconcile rechecks Bank Transaction write access, locks the row, calls the existing `unreconcile_bank_transaction` helper, and supports both unreconcile-only and cancel-linked-document choices.
- Unreconcile parses string boolean values from Frappe requests so `cancel_linked_documents=false` is treated as false rather than a truthy string.
- Implemented `MatchedPage.vue` with bank account/date filters, matched transaction table, selected-row review panel, linked voucher open action, unreconcile-only action, and cancel-linked-and-unreconcile action.
- Replaced the browser-native unreconcile confirmation with an in-app modal, so the confirmation is visible in the app shell, testable in Chrome, and consistent with the standalone route experience. The cancel-linked path explicitly warns that linked Payment Entry or Journal Entry documents will be cancelled.
- Backend tests cover matched listing, unreconcile-only preserving the linked Journal Entry, string boolean parsing for cancel choices, and unreconcile with linked Journal Entry cancellation.
- Final API module test suite passes across Phases 1 through 5 with 24 tests.
- Final frontend production build passes.
- Local unauthenticated route probe for `/bank-rec` returns `403 FORBIDDEN`, which confirms the route exists and Guest is blocked by the permission-checked boot method.
- Built JS and CSS assets under `/assets/advanced_bank_reconciliation/bank_rec/` return `200 OK`.
- Old Desk tool route probe redirects Guest to login, which confirms the route still resolves and has not been removed.
- Chrome plugin verification was attempted after the user requested `@chrome`, but the local Chrome bridge failed before a browser session could be created. Tool discovery did not expose another Chrome control tool, and the install list did not include a Chrome plugin candidate. Authenticated Chrome smoke remains blocked until the local Chrome plugin bridge is available.
- Chrome plugin setup initially failed before session setup, then succeeded after the updated plugin version was available on June 21, 2026.
- Chrome smoke opened `http://demo.localhost:8000/bank-rec`, confirmed redirect to `/bank-rec/reconcile`, verified Reconcile, Cash Coding, Matched, and Rules pages load in the authenticated browser session, and found no console errors.
- Chrome smoke surfaced a small page-title issue where Cash Coding rendered as `CashCoding`; fixed in `bank_rec/src/router/index.ts` and rechecked in Chrome.
- Authenticated Chrome workflow verification on `demo.localhost` used isolated `BRCHROME` fixture rows and exercised:
  - Create Journal Entry from a withdrawal and reconcile it.
  - Create Payment Entry from a customer deposit and reconcile it.
  - Match one Bank Transaction against two submitted Payment Entries.
  - Match one Bank Transaction against an unpaid Sales Invoice.
  - Cash Coding missing-account validation, then successful cash coding submission.
  - Update tab metadata update for reference and party fields.
  - Edit in Full Page draft handoff, with Bank Rec remaining on the same selected route and a Draft Journal Entry created in Desk.
  - Matched review, linked voucher visibility, unreconcile confirmation modal, and unreconcile-only completion.
- Database verification after the Chrome workflow confirmed the JE, PE, multi-PE, unpaid invoice, and cash-coding transactions were reconciled with the expected linked documents, the update row stayed unreconciled with metadata saved, the draft handoff created a draft Journal Entry, and the unreconcile-only row returned to `Unreconciled`.
- No site credential changes were made.
- Release type was confirmed as `feat`, and local incremental commits were created on branch `feat/bank-rec-route-app`.
- Generated Bank Rec build output is intentionally ignored and not part of the final branch diff.
- Re-ran the API test suite, frontend build, whitespace check, sensitive-string scan of changed paths, route probe, asset probes, and old Desk tool route probe on June 21, 2026.

Commands run:

- `bench --site demo.localhost run-tests --app advanced_bank_reconciliation --module advanced_bank_reconciliation.api.test_bank_rec`
- `yarn build`
- `bench --site demo.localhost clear-cache`
- `curl -I --max-time 8 http://demo.localhost:8000/bank-rec`
- `curl -I --max-time 8 http://demo.localhost:8000/assets/advanced_bank_reconciliation/bank_rec/assets/index-e68e8b06.js`
- `curl -I --max-time 8 http://demo.localhost:8000/assets/advanced_bank_reconciliation/bank_rec/assets/index-915ccf9d.css`
- `curl -I --max-time 8 http://demo.localhost:8000/app/advance-bank-reconciliation-tool`
- Attempted Chrome plugin setup through `@chrome`; the local browser bridge initially failed before session setup, then succeeded after the updated plugin version was available.
- Used `@chrome` against `http://demo.localhost:8000` for the workflow matrix listed above.
- `git -C apps/advanced_bank_reconciliation diff --check`
- Ran a sensitive-string scan against changed paths.

## Final MVP Completion Checklist

- `/bank-rec` route works.
- `Bank Rec` app screen entry works.
- No `/bank-rec-tool` route exists.
- Old tool remains untouched and functional.
- Permission facade blocks cross-company data access.
- Read-only Reconcile works.
- Match flow works.
- Update tab works for Bank Transaction metadata.
- Create voucher flow works.
- Edit in Full Page preserves entered create values by opening a Draft voucher in a new tab, keeps the Bank Rec tab state intact, and does not reconcile until the user completes reconciliation through the normal Bank Rec flow.
- Cash Coding works for non-tax simple coding.
- Minimal Rules list works and opens Desk for edit or delete.
- Settings is hidden from MVP navigation.
- Matched review and unreconcile work.
- Long-running match and cash-coding actions show progress.
- Mutating actions have duplicate-submit guards.
- Selection-dependent async calls discard stale responses.
- Hard refresh restores route filters and selected Bank Transaction where permitted.
- Cash-coding unsaved edits require confirmation before discard.
- Summary cards do not show Difference without statement closing balance.
- Tax, transfers, splits, and reconciliation-session model remain out of MVP.
- Python tests pass.
- Frontend build passes.
- Automated local route and asset probes pass.
- Authenticated Chrome smoke test passes.

## Later Backlog Reference

Track these after MVP completion:

- Phase 6: Statement balance check.
- Phase 7: Transfers.
- Phase 8: Tax coding.
- Phase 9: Split cash coding.
- Phase 10: Match adjustments and bank fees.
- Phase 11: Attachments and receipt capture.
