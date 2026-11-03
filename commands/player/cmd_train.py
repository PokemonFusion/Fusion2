"""Ordinary persistent Training Grounds sessions and explicit EV reset reviews."""

from evennia import Command


class CmdTrain(Command):
    """Train a chosen stat or freely change your EV investment.

    Usage:
      +train
      +train <party slot, full ID or fusion>=<HP||Attack||Defense||SpA||SpD||Speed>
      +train confirm
      +train continue <technique||pace||recovery>
      +train reset <target>=<stat>[/<amount>]
      +train reset <target>=all
      +train cancel

    At Training Grounds, preview and confirm a free session. Complete three
    active exercises at least 30 seconds apart for up to 64 EVs in your chosen
    stat (252 /stat,510 total). Reconnect keeps the session; time alone gives
    nothing. All exercise choices have the same numerical effect. Status and
    cancellation work anywhere. A fainted target cannot exercise.

    Reset previews a partial/stat/full EV removal and its HP/stat consequences.
    Confirm within five minutes. Reset is free and never gives rewards; cancel
    an active session first. Ordinary battle EV/EXP and genetic IVs are preserved.

    Useful session milestones: Rare Candy each 6, Bottle Cap each 12 and a one-time
    Gold Bottle Cap at 60. Existing item eligibility still applies. No EXP, PP or
    healing is granted; maximum-HP changes preserve the existing HP deficit.
    """

    key = "+train"
    locks = "cmd:all()"
    help_category = "Pokemon/Training"

    def func(self):
        """Parse deliberate actions; only the service may write progress or resources."""
        from pokemon.services.training_grounds import TrainingGrounds, TrainingError

        text = (self.args or "").strip()
        if text.casefold() == "help":
            self.caller.msg(self.__doc__)
            return
        service = TrainingGrounds(self.caller)
        try:
            if not text or text.casefold() == "status":
                result = service.status()
            elif text.casefold() == "confirm":
                result = service.confirm()
            elif text.casefold() == "cancel":
                result = service.cancel()
            elif text.casefold().startswith("continue "):
                result = service.advance(text.partition(" ")[2].strip().casefold())
            else:
                reset = text.casefold().startswith("reset ")
                selection = text.partition(" ")[2].strip() if reset else text
                target, separator, stat = selection.partition("=")
                if not separator or not target.strip() or not stat.strip():
                    raise TrainingError("Use +train <target>=<stat> or +train reset <target>=<stat>[/<amount>]. See +train help.")
                amount = None
                if "/" in stat:
                    stat, separator, number = stat.partition("/")
                    if not reset or not number.strip().isascii() or not number.strip().isdigit():
                        raise TrainingError("A partial reset accepts one whole EV amount from 1 through 252.")
                    amount = int(number.strip())
                result = service.review(target.strip(), stat.strip(), reset=reset, amount=amount)
            service.notify(result)
        except TrainingError as error:
            self.caller.msg(str(error))
        except Exception:
            from evennia.utils import logger

            logger.log_trace("Training request failed")
            self.caller.msg("Training could not be saved. Nothing changed; inspect +train and try again.")
