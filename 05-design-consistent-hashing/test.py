from statistics import mean

from consistent_hash import ConsistentHash, Node
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
            nodes=[
                Node(id=1),
                Node(id=2),
                Node(id=3),
            ],
        )
        initial_key_to_node = {}
        for key in initial_data:
            node = consistent_hash.get_node_of_key(key)
            initial_key_to_node[key] = node

        consistent_hash.add_node(Node(id=4))  # 추가와 동시에 재배치도 끝나야 함.
        after_key_to_node = {}
        for key in initial_data:
            node = consistent_hash.get_node_of_key(key)
            after_key_to_node[key] = node

        n_diff = 0  # 재배치(rehashing)된 수
        for key in initial_data:
            if initial_key_to_node[key] != after_key_to_node[key]:
                n_diff += 1
        n_diffs.append(n_diff)

    assert int(mean(n_diffs)) == int(len(initial_data) / 4)  # 재배치된 수의 평균은 n/k와 같아야 함.
