import time


class SnowflakeIdGenerator:
    _SEQUENCE_NUMBER_BITS = 12
    _MACHINE_ID_BITS = 5
    _DATACENTER_ID_BITS = 5
    _TIMESTAMP_BITS = 41

    _MAX_SEQUENCE_NUMBER = (1 << _SEQUENCE_NUMBER_BITS) - 1
    _MAX_MACHINE_ID = (1 << _MACHINE_ID_BITS) - 1
    _MAX_DATACENTER_ID = (1 << _DATACENTER_ID_BITS) - 1

    def __init__(
        self,
        data_center_id: int,
        machine_id: int,
        epoch: int = int(time.mktime((2021, 1, 1, 0, 0, 0, 0, 0, 0))),
    ) -> None:
        if data_center_id > self._MAX_DATACENTER_ID:
            raise ValueError(
                f"data_center_id value must be less than or equal to {self._MAX_DATACENTER_ID}"
            )
        if machine_id > self._MAX_MACHINE_ID:
            raise ValueError(
                f"machine_id value must be less than or equal to {self._MAX_MACHINE_ID}"
            )

        self.data_center_id = data_center_id
        self.machine_id = machine_id
        self.epoch = epoch
        self._last_generate_ts = None
        self._last_sequence_number = 0

    def generate(self) -> int:
        id_ = (
            (
                1
                << (
                    self._SEQUENCE_NUMBER_BITS
                    + self._MACHINE_ID_BITS
                    + self._DATACENTER_ID_BITS
                    + self._TIMESTAMP_BITS
                )
            )
            | (
                self._timestamp
                << (
                    self._SEQUENCE_NUMBER_BITS
                    + self._MACHINE_ID_BITS
                    + self._DATACENTER_ID_BITS
                )
            )
            | (
                self.data_center_id
                << (self._SEQUENCE_NUMBER_BITS + self._MACHINE_ID_BITS)
            )
            | (self.machine_id << (self._SEQUENCE_NUMBER_BITS))
            | self._sequence_number
        )
        self._last_generate_ts = int(time.time() * 1000)
        return id_

    @property
    def _timestamp(self) -> int:
        return int((time.time()) * 1000) - self.epoch

    @property
    def _sequence_number(self) -> int:
        if self._last_generate_ts is None:
            self._last_sequence_number = 0
        elif ((time.time() * 1000) - self._last_generate_ts) > 1:
            self._last_sequence_number = 0
        else:
            self._last_sequence_number += 1
        if self._last_sequence_number > self._MAX_SEQUENCE_NUMBER:
            raise Exception(
                "The sequence number has been exhausted. Please try again in a moment."
            )
        return self._last_sequence_number
