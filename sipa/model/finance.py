from abc import ABCMeta, abstractmethod

from flask_babel import gettext

from sipa.model.fancy_property import ActiveProperty, Capabilities
from sipa.units import format_money


class BaseFinanceInformation(metaclass=ABCMeta):
    """A Class providing finance information about a user.

    This class bundles informations such as whether the current user
    is obliged to pay, the current balance, history, and the time of
    the last update.  The balance is being provided as a
    FancyProperty, so it can be used as a row.

    For subclassing, implement the respective abstract
    methods/properties.
    """

    @property
    def balance(self):
        """The current balance as a
        :py:class:`~sipa.model.fancy_property.ActiveProperty`

        If :attr:`has_to_pay` is False, return an empty property with
        the note that the user doesn't have to pay.  Else, return the
        balance formatted and styled (red/green) as money and mark
        this property editable.
        """
        if not self.has_to_pay:
            return ActiveProperty('balance', value=gettext("Muss nicht bezahlen"),
                                  raw_value=0, empty=True)
        return ActiveProperty('balance', value=format_money(self._balance),
                              raw_value=self._balance,
                              capabilities=Capabilities(edit=True, delete=False))

    @property
    @abstractmethod
    def _balance(self) -> float:
        """**[Abstract]** The current balance

        If :py:meth:`has_to_pay` is False, this method will not be
        used implicitly.
        """
        pass

    @property
    @abstractmethod
    def has_to_pay(self) -> bool:
        """**[Abstract]** Whether the user is obliged to pay."""
        pass

    @property
    @abstractmethod
    def history(self):
        """**[Abstract]** History of payments

        This method should return an iterable of a (datetime, int)
        tuple.
        """
        pass

    @property
    @abstractmethod
    def last_update(self):
        """**[Abstract]** The time of the last update."""
        pass
