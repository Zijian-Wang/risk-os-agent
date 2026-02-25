# RiskOS Heartbeat

## Portfolio

- [ ] Pull positions via schwab-portfolio
- [ ] Check portfolio daily P&L vs `config/risk-rules.yaml` `hard_alerts.portfolio_daily_down_pct` → ALERT on breach
- [ ] Check stop proximity via risk-calculator using `hard_alerts.stop_approaching_pct` → ALERT if approaching/hit (long + short direction aware)

## Phase & Technical

- [ ] Get phases for all positions via phase-analyzer (one TA method)
- [ ] Flag phase transitions listed in `hard_alerts.phase_transition_pairs` → ALERT
- [ ] Flag HMA dead cross / trend shift → soft flag
- [ ] Other TA (RSI, MACD, etc.) → soft flags, on-demand Q&A

## External

- [ ] Check market-news for adversarial research, major news → ALERT
- [ ] Consecutive down days (`soft_flags.consecutive_down_days`), strong performers, concentration (`soft_flags.concentration_warn_pct`) → soft flag for briefing

Respond with `HEARTBEAT_OK` when nothing actionable; only send when there is something to report.
