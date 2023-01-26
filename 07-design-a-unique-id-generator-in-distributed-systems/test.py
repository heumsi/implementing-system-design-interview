from snowflake_id_generator import SnowflakeIdGenerator


def test_generator():
    # given
    id_generator = SnowflakeIdGenerator(data_center_id=1, machine_id=1)

    # when
    ids = [id_generator.generate() for _ in range(10)]

    # then
    assert all([type(id_) == int for id_ in ids])
    assert all([id_.bit_length() == 64 for id_ in ids])
    assert ids == list(set(ids))
    assert ids == sorted(ids)
