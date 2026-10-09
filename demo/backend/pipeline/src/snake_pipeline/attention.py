import torch
from torch import nn


class SEBlock(nn.Module):
    def __init__(self, channels, reduction=16):
        super().__init__()
        if reduction <= 0:
            raise ValueError("SE reduction must be positive")
        hidden = max(1, channels // reduction)
        self.block = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Conv2d(channels, hidden, 1),
                                   nn.ReLU(inplace=True), nn.Conv2d(hidden, channels, 1), nn.Sigmoid())
    def forward(self, x): return x * self.block(x)


class CBAM(nn.Module):
    def __init__(self, channels, reduction=16, spatial_kernel=7):
        super().__init__()
        if reduction <= 0:
            raise ValueError("CBAM reduction must be positive")
        if spatial_kernel <= 0 or spatial_kernel % 2 == 0:
            raise ValueError("CBAM spatial kernel must be a positive odd number")
        hidden = max(1, channels // reduction)
        self.channel = nn.Sequential(nn.Conv2d(channels, hidden, 1), nn.ReLU(inplace=True), nn.Conv2d(hidden, channels, 1))
        self.spatial = nn.Conv2d(2, 1, spatial_kernel, padding=spatial_kernel // 2, bias=False)
    def forward(self, x):
        channel = torch.sigmoid(self.channel(torch.mean(x, (2, 3), keepdim=True)) +
                                self.channel(torch.amax(x, (2, 3), keepdim=True)))
        x = x * channel
        spatial = torch.sigmoid(self.spatial(torch.cat([torch.mean(x, 1, keepdim=True), torch.amax(x, 1, keepdim=True)], 1)))
        return x * spatial
