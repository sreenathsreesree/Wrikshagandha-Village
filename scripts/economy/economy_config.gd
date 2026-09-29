extends Resource
class_name EconomyConfig

## Economy configuration (M05.4, D-23). Holds the long-term redemption
## reference of D-10 — 1000 coins = ₹10 — as configuration for a separate,
## future backend/redemption phase ONLY. No gameplay code reads this: it is
## not the Wallet's, not a points ↔ coins rate (O-02) and never shown in the
## UI. Real money, payments and crypto are out of scope (D-10, O-03).
##
## Earn amounts are not here: flat rewards are RewardRule data
## (data/rewards/, M05.3); per-definition amounts stay on discoveries and
## crops; FarmManager's QUALITY_POINT_SCALE is a frozen farm-quality rule.

## Coins in one redemption unit (reference only).
@export var redemption_reference_coins: int = 1000
## What that many coins would be worth, in redemption_reference_currency.
@export var redemption_reference_amount: int = 10
## ISO 4217 code of the reference amount.
@export var redemption_reference_currency: String = "INR"
