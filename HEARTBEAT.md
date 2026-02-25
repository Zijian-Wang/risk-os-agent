# RiskOS Heartbeat

## Portfolio

- [ ] Pull positions via schwab-portfolio
- [ ] Check portfolio daily P&L > 1% down → ALERT
- [ ] Check stop proximity via risk-calculator → ALERT if approaching/hit

## Phase & Technical

- [ ] Get phases for all positions via phase-analyzer (one TA method)
- [ ] Flag phase transitions (3→4, 4→5) → ALERT
- [ ] Flag HMA dead cross / trend shift → soft flag
- [ ] Other TA (RSI, MACD, etc.) → soft flags, on-demand Q&A

## External

- [ ] Check market-news for adversarial research, major news → ALERT
- [ ] Consecutive down days, strong performers → soft flag for briefing

Respond with `HEARTBEAT_OK` when nothing actionable; only send when there is something to report.
