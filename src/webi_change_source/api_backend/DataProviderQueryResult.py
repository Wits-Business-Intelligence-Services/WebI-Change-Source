from dataclasses import dataclass


@dataclass
class DataProviderQueryResult:
    data_source_id: int
    data_source_type: str
    id: str
    name: str

    def print(
        self,
    ):
        print(f"name: {self.name}")
        print(f"data_source_id: {self.data_source_id}")
        print(f"data_source_type: {self.data_source_type}")
        print(f"id: {self.id}")
