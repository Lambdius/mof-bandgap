from dataclasses import dataclass

import torch  # pyright: ignore[reportMissingImports]
from sklearn.metrics import mean_absolute_error, r2_score  # type: ignore[import-untyped]
from torch import nn, optim  # pyright: ignore[reportMissingImports]

from mof_bandgap.constants import (
    CGCNN_ATOM_EMBED_DIM,
    CGCNN_EARLY_STOPPING_PATIENCE,
    CGCNN_EPOCHS,
    CGCNN_HIDDEN_DIM,
    CGCNN_LEARNING_RATE,
    CGCNN_MAX_ATOMIC_NUMBER,
    CGCNN_N_CONV_LAYERS,
    CGCNN_RANDOM_STATE,
    CGCNN_RBF_BINS,
    CGCNN_RBF_WIDTH,
    CGCNN_WEIGHT_DECAY,
    GRAPH_CUTOFF_RADIUS,
)
from mof_bandgap.infrastructure.database.models import Features
from mof_bandgap.train.models.base import Metrics


def _scatter_mean(values: torch.Tensor, index: torch.Tensor, dim_size: int) -> torch.Tensor:
    out = torch.zeros(dim_size, values.shape[-1], dtype=values.dtype)
    out.index_add_(0, index, values)
    counts = torch.zeros(dim_size, dtype=values.dtype)
    counts.index_add_(0, index, torch.ones(index.shape[0], dtype=values.dtype))
    return out / counts.clamp(min=1.0).unsqueeze(-1)


@dataclass
class BatchedGraph:
    atomic_numbers: torch.Tensor
    edge_index:     torch.Tensor
    edge_distances: torch.Tensor
    batch_index:    torch.Tensor
    descriptors:    torch.Tensor
    n_graphs:       int


def _sample_descriptors(sample: Features) -> list[float]:
    return (
        sample.metal_descriptors
        + sample.metal2_descriptors
        + [sample.has_interior_metal]
        + sample.structural_descriptors
        + sample.linker_descriptors
    )


def _collate_graphs(samples: list[Features]) -> BatchedGraph:
    atomic_numbers: list[int]         = []
    edge_index:     list[list[int]]   = []
    edge_distances: list[float]       = []
    batch_index:    list[int]         = []
    descriptors:    list[list[float]] = []

    offset = 0
    for graph_idx, sample in enumerate(samples):
        atomic_numbers.extend(sample.atomic_numbers)
        batch_index.extend([graph_idx] * len(sample.atomic_numbers))
        descriptors.append(_sample_descriptors(sample))
        for (i, j), distance in zip(sample.edge_index, sample.edge_distances, strict=True):
            edge_index.append([i + offset, j + offset])
            edge_distances.append(distance)
        offset += len(sample.atomic_numbers)

    return BatchedGraph(
        atomic_numbers = torch.tensor(atomic_numbers, dtype=torch.long).clamp(max=CGCNN_MAX_ATOMIC_NUMBER),
        edge_index     = torch.tensor(edge_index, dtype=torch.long),
        edge_distances = torch.tensor(edge_distances, dtype=torch.float32),
        batch_index    = torch.tensor(batch_index, dtype=torch.long),
        descriptors    = torch.tensor(descriptors, dtype=torch.float32),
        n_graphs       = len(samples),
    )


class GaussianExpansion(nn.Module):
    centers: torch.Tensor

    def __init__(self, bins: int, width: float, cutoff: float) -> None:
        super().__init__()
        self.register_buffer("centers", torch.linspace(0.0, cutoff, bins))
        self.width = width

    def forward(self, distances: torch.Tensor) -> torch.Tensor:
        diff = distances.unsqueeze(-1) - self.centers
        result: torch.Tensor = torch.exp(-(diff**2) / (2 * self.width**2))
        return result


class GraphConvLayer(nn.Module):
    def __init__(self, hidden_dim: int, edge_dim: int) -> None:
        super().__init__()
        self.edge_mlp    = nn.Sequential(nn.Linear(edge_dim, hidden_dim), nn.ReLU())
        self.message_mlp = nn.Sequential(nn.Linear(hidden_dim * 2, hidden_dim), nn.ReLU())
        self.update_mlp  = nn.Sequential(nn.Linear(hidden_dim * 2, hidden_dim), nn.ReLU())

    def forward(self, node_feat: torch.Tensor, edge_index: torch.Tensor, edge_feat: torch.Tensor) -> torch.Tensor:
        target_idx   = edge_index[:, 0]
        neighbor_idx = edge_index[:, 1]

        edge_message = self.edge_mlp(edge_feat)
        h_neighbor   = node_feat[neighbor_idx]
        message      = self.message_mlp(torch.cat([h_neighbor, edge_message], dim=-1))
        aggregated   = _scatter_mean(message, target_idx, node_feat.shape[0])

        result: torch.Tensor = self.update_mlp(torch.cat([node_feat, aggregated], dim=-1)) + node_feat
        return result


class CGCNNNet(nn.Module):
    def __init__(
        self,
        descriptor_dim:    int,
        hidden_dim:        int   = CGCNN_HIDDEN_DIM,
        n_conv:            int   = CGCNN_N_CONV_LAYERS,
        atom_embed_dim:    int   = CGCNN_ATOM_EMBED_DIM,
        rbf_bins:          int   = CGCNN_RBF_BINS,
        rbf_width:         float = CGCNN_RBF_WIDTH,
        cutoff:            float = GRAPH_CUTOFF_RADIUS,
        max_atomic_number: int   = CGCNN_MAX_ATOMIC_NUMBER,
    ) -> None:
        super().__init__()
        self.atom_embed = nn.Embedding(max_atomic_number + 1, atom_embed_dim)
        self.node_proj  = nn.Linear(atom_embed_dim, hidden_dim)
        self.rbf        = GaussianExpansion(rbf_bins, rbf_width, cutoff)
        self.convs      = nn.ModuleList([GraphConvLayer(hidden_dim, rbf_bins) for _ in range(n_conv)])
        self.head       = nn.Sequential(nn.Linear(hidden_dim + descriptor_dim, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, batch: BatchedGraph) -> torch.Tensor:
        h         = self.node_proj(self.atom_embed(batch.atomic_numbers))
        edge_feat = self.rbf(batch.edge_distances)
        for conv in self.convs:
            h = conv(h, batch.edge_index, edge_feat)

        graph_embed = _scatter_mean(h, batch.batch_index, batch.n_graphs)
        combined = torch.cat([graph_embed, batch.descriptors], dim=-1)
        result: torch.Tensor = self.head(combined).squeeze(-1)
        return result


class CGCNNModel:
    def evaluate(self, train: list[Features], val: list[Features]) -> Metrics:
        train_batch = _collate_graphs(train)
        val_batch   = _collate_graphs(val)
        y_train     = torch.tensor([sample.band_gap for sample in train], dtype=torch.float32)
        y_val       = torch.tensor([sample.band_gap for sample in val], dtype=torch.float32)

        self._standardize_descriptors(train_batch, val_batch)

        torch.manual_seed(CGCNN_RANDOM_STATE)
        net = CGCNNNet(descriptor_dim=train_batch.descriptors.shape[1])
        model = self._train(net, train_batch, y_train, val_batch, y_val)

        model.eval()
        with torch.no_grad():
            predictions = model(val_batch).numpy()

        target = y_val.numpy()
        return Metrics(mae=float(mean_absolute_error(target, predictions)), r2=float(r2_score(target, predictions)))

    @staticmethod
    def _standardize_descriptors(train_batch: BatchedGraph, val_batch: BatchedGraph) -> None:
        mean = train_batch.descriptors.mean(dim=0, keepdim=True)
        std = train_batch.descriptors.std(dim=0, keepdim=True).clamp(min=1e-6)
        train_batch.descriptors = (train_batch.descriptors - mean) / std
        val_batch.descriptors = (val_batch.descriptors - mean) / std

    @staticmethod
    def _train(
        model:       CGCNNNet,
        train_batch: BatchedGraph,
        y_train:     torch.Tensor,
        val_batch:   BatchedGraph,
        y_val:       torch.Tensor,
    ) -> CGCNNNet:
        optimizer = optim.Adam(model.parameters(), lr=CGCNN_LEARNING_RATE, weight_decay=CGCNN_WEIGHT_DECAY)
        loss_fn = nn.MSELoss()

        best_val_loss = float("inf")
        best_state: dict[str, torch.Tensor] | None = None
        epochs_without_improvement = 0

        for _ in range(CGCNN_EPOCHS):
            model.train()
            optimizer.zero_grad()
            loss = loss_fn(model(train_batch), y_train)
            loss.backward()
            optimizer.step()

            model.eval()
            with torch.no_grad():
                val_loss = loss_fn(model(val_batch), y_val).item()

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
        return model
