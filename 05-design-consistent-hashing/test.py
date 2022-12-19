from collections import Counter
from statistics import mean

from consistent_hash import ConsistentHash, Node
from faker import Faker


def test_get_node_of_key_successfully():
    # given
    consistent_hash = ConsistentHash(
        nodes=[
            Node(id="1"),
            Node(id="2"),
            Node(id="3"),
        ],
    )
    faker = Faker()

    n_data = 10
    for _ in range(n_data):

        # when
        key = faker.email()
        node = consistent_hash.get_node_of_key(key)

        # then
        assert node.id in ["1", "2", "3"]


def test_get_node_of_key_should_divide_the_keys_evenly():
    # given
    nodes = [
        Node(id="1"),
        Node(id="2"),
        Node(id="3"),
    ]
    consistent_hash = ConsistentHash(nodes=nodes)
    faker = Faker()
    node_ids = []

    # when
    n_data_per_node = 100
    n_data = n_data_per_node * len(nodes)
    for _ in range(n_data):
        key = faker.email()
        node = consistent_hash.get_node_of_key(key)
        node_ids.append(node.id)

    # then
    counter = Counter(node_ids)
    error_rate = 0.05
    lower_bound = n_data_per_node - int(n_data_per_node * error_rate)
    upper_bound = n_data_per_node + int(n_data_per_node * error_rate)
    expected_values = list(range(lower_bound, upper_bound))
    assert counter["1"] in expected_values
    assert counter["2"] in expected_values
    assert counter["3"] in expected_values


def test_content_hash_do_successfully():
    n_test = 100
    n_diffs = []
    faker = Faker()
    n_data = 10
    initial_data = [faker.email() for _ in range(n_data)]
    for _ in range(n_test):
        consistent_hash = ConsistentHash(
            nodes=[
                Node(id="1"),
                Node(id="2"),
                Node(id="3"),
            ],
        )
        initial_key_to_node = {}
        for key in initial_data:
            node = consistent_hash.get_node_of_key(key)
            initial_key_to_node[key] = node

        consistent_hash.add_node(Node(id="4"))  # 추가와 동시에 재배치도 끝나야 함.
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
