extends Resource
class_name RewardRule

## One Wriksha Points reward as data (M05.3): what a one-time or recurring
## reward pays, so amounts change without code. Rewards whose amount lives
## on another definition keep it there — a discovery's points_value, a
## crop's points_value (scaled by FarmManager's quality rule). Points only:
## coins come with O-02 (M05.5) / M06.2.

## Stable, lower_snake_case, equal to the file name; the reward's code id.
@export var id: String = ""
## Wriksha Points paid, >= 0.
@export var points: int = 0
## For count-based rewards only (the discovery-count thresholds): the count
## that pays. 0 = not a threshold reward.
@export var threshold: int = 0
