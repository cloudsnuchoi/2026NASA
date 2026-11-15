"""Prithvi-EO-1.0-100M multi-temporal crop classification — inference-only forward pass in plain PyTorch.

Re-implements, without mmseg/mmcv, the modules named in the released config
(ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification, Apache-2.0,
code: NASA-IMPACT/hls-foundation-os `geospatial_fm`):
  TemporalViTEncoder (6 blocks, 768 dim, 8 heads, patch 16, tubelet 1, 3 frames)
  -> ConvTransformerTokensToEmbeddingNeck (drop cls, 2x fpn ConvTranspose 14->224)
  -> FCNHead (1 conv 3x3 + BN + ReLU, 1x1 conv_seg, 13 classes).
The auxiliary head is training-only and is not used. No fine-tuning happens here.

Input pre-processing replicates the released test pipeline exactly: an (H, W, 18) stack ordered
t1[B,G,R,NIR,SW1,SW2], t2[...], t3[...] in HLS scaled reflectance (DN, x1e-4), permuted to (18, H, W),
normalised per channel with the config means/stds, then `reshape(6, 3, H, W)` (plain reshape, as in
the released `Reshape` transform the model was trained with).
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

MODEL_ID = "ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification"
CKPT_NAME = "multi_temporal_crop_classification_Prithvi_100M.pth"

# Official class order (model card / config CLASSES; labels 1..13, reduce_zero_label -> index 0..12).
CLASSES = (
    "Natural Vegetation",
    "Forest",
    "Corn",
    "Soybeans",
    "Wetlands",
    "Developed/Barren",
    "Open Water",
    "Winter Wheat",
    "Alfalfa",
    "Fallow/Idle Cropland",
    "Cotton",
    "Sorghum",
    "Other",
)
_MEANS6 = [494.905781, 815.239594, 924.335066, 2968.881459, 2634.621962, 1739.579917]
_STDS6 = [284.925432, 357.84876, 575.566823, 896.601013, 951.900334, 921.407808]
MEANS = np.array(_MEANS6 * 3, dtype=np.float32)
STDS = np.array(_STDS6 * 3, dtype=np.float32)

EMBED, HEADS, DEPTH, PATCH, FRAMES, IMG = 768, 8, 6, 16, 3, 224
HP = IMG // PATCH


class Attention(nn.Module):
    def __init__(self, dim, heads):
        super().__init__()
        self.h = heads
        self.qkv = nn.Linear(dim, dim * 3, bias=True)
        self.proj = nn.Linear(dim, dim)

    def forward(self, x):
        b, n, c = x.shape
        q, k, v = self.qkv(x).reshape(b, n, 3, self.h, c // self.h).permute(2, 0, 3, 1, 4)
        x = F.scaled_dot_product_attention(q, k, v)
        return self.proj(x.transpose(1, 2).reshape(b, n, c))


class Mlp(nn.Module):
    def __init__(self, dim, hidden):
        super().__init__()
        self.fc1 = nn.Linear(dim, hidden)
        self.fc2 = nn.Linear(hidden, dim)

    def forward(self, x):
        return self.fc2(F.gelu(self.fc1(x)))


class Block(nn.Module):  # timm ViT block (pre-norm)
    def __init__(self, dim, heads):
        super().__init__()
        self.norm1 = nn.LayerNorm(dim)
        self.attn = Attention(dim, heads)
        self.norm2 = nn.LayerNorm(dim)
        self.mlp = Mlp(dim, dim * 4)

    def forward(self, x):
        x = x + self.attn(self.norm1(x))
        return x + self.mlp(self.norm2(x))


class PatchEmbed(nn.Module):
    def __init__(self):
        super().__init__()
        self.proj = nn.Conv3d(6, EMBED, kernel_size=(1, PATCH, PATCH), stride=(1, PATCH, PATCH))

    def forward(self, x):  # B,C,T,H,W -> B, T*Hp*Wp, D
        return self.proj(x).flatten(2).transpose(1, 2)


class Backbone(nn.Module):
    def __init__(self):
        super().__init__()
        self.patch_embed = PatchEmbed()
        self.cls_token = nn.Parameter(torch.zeros(1, 1, EMBED))
        self.pos_embed = nn.Parameter(torch.zeros(1, 1 + FRAMES * HP * HP, EMBED), requires_grad=False)
        self.blocks = nn.ModuleList([Block(EMBED, HEADS) for _ in range(DEPTH)])
        self.norm = nn.LayerNorm(EMBED)

    def forward(self, x):
        x = self.patch_embed(x) + self.pos_embed[:, 1:, :]
        cls = (self.cls_token + self.pos_embed[:, :1, :]).expand(x.shape[0], -1, -1)
        x = torch.cat([cls, x], dim=1)
        for b in self.blocks:
            x = b(x)
        return self.norm(x)


class Norm2d(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.ln = nn.LayerNorm(dim, eps=1e-6)

    def forward(self, x):
        return self.ln(x.permute(0, 2, 3, 1)).permute(0, 3, 1, 2)


class Neck(nn.Module):
    def __init__(self):
        super().__init__()
        d = EMBED * FRAMES

        def up():
            return nn.Sequential(nn.ConvTranspose2d(d, d, 2, 2), Norm2d(d), nn.GELU(), nn.ConvTranspose2d(d, d, 2, 2))

        self.fpn1, self.fpn2 = up(), up()

    def forward(self, x):
        x = x[:, 1:, :]
        x = x.permute(0, 2, 1).reshape(x.shape[0], -1, HP, HP)
        return self.fpn2(self.fpn1(x))


class ConvModule(nn.Module):
    def __init__(self, cin, cout):
        super().__init__()
        self.conv = nn.Conv2d(cin, cout, 3, padding=1, bias=False)
        self.bn = nn.BatchNorm2d(cout)

    def forward(self, x):
        return F.relu(self.bn(self.conv(x)))


class FCNHead(nn.Module):
    def __init__(self):
        super().__init__()
        self.convs = nn.Sequential(ConvModule(EMBED * FRAMES, 256))
        self.conv_seg = nn.Conv2d(256, len(CLASSES), 1)

    def forward(self, x):
        return self.conv_seg(self.convs(x))


class PrithviCrop(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = Backbone()
        self.neck = Neck()
        self.decode_head = FCNHead()

    def forward(self, x):
        return self.decode_head(self.neck(self.backbone(x)))


def load(ckpt_path: str) -> PrithviCrop:
    sd = torch.load(ckpt_path, map_location="cpu", weights_only=False)["state_dict"]
    sd = {k: v for k, v in sd.items() if not k.startswith("auxiliary_head.")}
    m = PrithviCrop()
    missing, unexpected = m.load_state_dict(sd, strict=False)
    missing = [k for k in missing if not k.endswith("num_batches_tracked")]
    if missing or unexpected:
        raise RuntimeError(f"checkpoint mismatch missing={missing} unexpected={unexpected}")
    return m.eval()


def preprocess(stack_hw18: np.ndarray) -> torch.Tensor:
    """(H, W, 18) HLS DN (fill already replaced) -> (1, 6, 3, H, W) normalised tensor."""
    x = (stack_hw18.astype(np.float32) - MEANS) / STDS
    x = torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1)))
    return x.reshape(6, 3, x.shape[1], x.shape[2]).unsqueeze(0)


@torch.no_grad()
def predict(model: PrithviCrop, stack_hw18: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Returns (class index map HxW, softmax probs 13xHxW) for a 224x224 chip."""
    logits = model(preprocess(stack_hw18))[0]
    p = logits.softmax(0)
    return p.argmax(0).numpy().astype(np.uint8), p.numpy()
