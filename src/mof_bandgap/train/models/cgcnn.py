import torch
from sklearn.metrics import mean_absolute_error, r2_score  # type: ignore[import-untyped]
from torch import nn, optim

from mof_bandgap.constants import (
    CGCNN_EARLY_STOPPING_PATIENCE,
    CGCNN_EPOCHS,
    CGCNN_HIDDEN_DIM,
    CGCNN_LEARNING_RATE,
    CGCNN_N_CONV_LAYERS,
    CGCNN_RANDOM_STATE,
    CGCNN_WEIGHT_DECAY,
)
from mof_bandgap.infrastructure.database.models import Features
from mof_bandgap.mapper import FeatureMapper
from mof_bandgap.train.models.base import Metrics


class EdgeConditionedUpdate(nn.Module):
    def __init__(self, node_dim: int, edge_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.edge_mlp = nn.Sequential(nn.Linear(edge_dim, hidden_dim), nn.ReLU())
        self.node_mlp = nn.Sequential(nn.Linear(node_dim + hidden_dim, node_dim), nn.ReLU())

    def forward(self, node_feat: torch.Tensor, edge_feat: torch.Tensor) -> torch.Tensor:
        message = self.edge_mlp(edge_feat)
        result: torch.Tensor = self.node_mlp(torch.cat([node_feat, message], dim=-1)) + node_feat
        return result


class MiniCGCNN(nn.Module):
    def __init__(
        self, node_dim: int, edge_dim: int, hidden_dim: int = CGCNN_HIDDEN_DIM, n_conv: int = CGCNN_N_CONV_LAYERS
    ) -> None:
        super().__init__()
        self.embed = nn.Linear(node_dim, hidden_dim)
        self.convs = nn.ModuleList([EdgeConditionedUpdate(hidden_dim, edge_dim, hidden_dim) for _ in range(n_conv)])
        self.head = nn.Sequential(nn.Linear(hidden_dim, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, node_feat: torch.Tensor, edge_feat: torch.Tensor) -> torch.Tensor:
        hidden = self.embed(node_feat)
        for conv in self.convs:
            hidden = conv(hidden, edge_feat)
        result: torch.Tensor = self.head(hidden).squeeze(-1)
        return result


class CGCNNModel:
    def evaluate(self, train: list[Features], val: list[Features]) -> Metrics:
        node_train, node_val = FeatureMapper.normalize(
            FeatureMapper.to_node_matrix(train), FeatureMapper.to_node_matrix(val)
        )
        edge_train, edge_val = FeatureMapper.normalize(
            FeatureMapper.to_edge_matrix(train), FeatureMapper.to_edge_matrix(val)
        )
        y_train = torch.tensor(FeatureMapper.to_target(train), dtype=torch.float32)
        y_val = torch.tensor(FeatureMapper.to_target(val), dtype=torch.float32)

        torch.manual_seed(CGCNN_RANDOM_STATE)

        model = MiniCGCNN(node_dim=node_train.shape[1], edge_dim=edge_train.shape[1])
        optimizer = optim.Adam(model.parameters(), lr=CGCNN_LEARNING_RATE, weight_decay=CGCNN_WEIGHT_DECAY)
        loss_fn = nn.MSELoss()

        best_val_loss = float("inf")
        best_state: dict[str, torch.Tensor] | None = None
        epochs_without_improvement = 0

        for _ in range(CGCNN_EPOCHS):
            model.train()
            optimizer.zero_grad()
            loss = loss_fn(model(node_train, edge_train), y_train)
            loss.backward()
            optimizer.step()

            model.eval()
            with torch.no_grad():
                val_loss = loss_fn(model(node_val, edge_val), y_val).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {key: value.clone() for key, value in model.state_dict().items()}
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1
                if epochs_without_improvement >= CGCNN_EARLY_STOPPING_PATIENCE:
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.eval()
        with torch.no_grad():
            predictions = model(node_val, edge_val).numpy()

        target = y_val.numpy()
        return Metrics(
            mae=float(mean_absolute_error(target, predictions)), r2=float(r2_score(target, predictions))
        )
