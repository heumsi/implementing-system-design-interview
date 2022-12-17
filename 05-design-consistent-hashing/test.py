from statistics import mean

from faker import Faker


def test_content_hash_do_successfully():
    n_test = 100
    n_diffs = []
    fake = Faker()
    n_data = 10
    initial_data = [fake.email() for _ in range(n_data)]
    for _ in range(n_test):
        consistent_hash = ConsistentHash(
            hash_algorithm="sha",
            n_node_indexes=3,  # 0보다 커야함.
        )
        initial_key_to_node_index = {}
        for key in initial_data:
            node_index = consistent_hash.get_node_index_by_key(key)
            initial_key_to_node_index[key] = node_index

        consistent_hash.add_node()  # 추가와 동시에 재배치도 끝나야 함.
        after_added_node_key_to_node_index = {}
        for key in initial_data:
            node_index = consistent_hash.get_node_index_by_key(key)
            after_added_node_key_to_node_index[key] = node_index

        n_diff = 0  # 재배치(rehashing)된 수
        for key in initial_data:
            if (
                initial_key_to_node_index[key]
                != after_added_node_key_to_node_index[key]
            ):
                n_diff += 1
        n_diffs.append(n_diff)

    assert int(mean(n_diffs)) == int(len(initial_data) / 4)  # 재배치된 수의 평균은 n/k와 같아야 함.
