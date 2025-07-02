from enum import Enum
from typing import Dict, List, Optional, NamedTuple, Callable, Tuple
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from constants import DEFAULT_VERSION

from .elements import BaseElement
from .graphics import EulerRotation, GraphicElement, Point, Point3D
from .layer import LayerRef


class AssemblyType(str, Enum):
    NONE = None  # Nothing to mount (i.e. not a package, just a footprint)
    THT = "tht"  # Pure THT package
    SMT = "smt"  # Pure SMT package
    MIXED = "mixed"  # Mixed THT/SMT package
    OTHER = "other"  # Anything special, e.g. mechanical parts
    AUTO = "auto"  # Auto detection (deprecated, only for file format migration!)


class PadShape(str, Enum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    OVAL = "oval"
    POLYGON = "polygon"
    ROUNDRECT = "roundrect"


class PadType(str, Enum):
    SMD = "smd"
    THROUGH_HOLE = "through_hole"
    VIA = "via"
    CONNECT = "connect"
    MECHANICAL = "mechanical"


class DrillShape(str, Enum):
    ROUND = "round"
    OBLONG = "oblong"


# --- Alignment Models ---


class AlignmentReference(NamedTuple):
    """Represents a reference point for alignment."""

    pad_number: str
    source_x: float  # Pixel position in PNG
    source_y: float  # Pixel position in PNG
    target_x: float  # Physical position in mm
    target_y: float  # Physical position in mm


class FootprintAlignment(BaseModel):
    """Container for footprint alignment data."""

    svg_to_png_scale: float
    reference_points: List[AlignmentReference]


# --- Pads and Drills ---


class Pad(BaseModel):
    number: str
    uuid: UUID
    pad_type: PadType = PadType.SMD
    shape: PadShape
    position: Point
    width: float
    height: Optional[float] = None
    rotation: float = 0.0
    layer: LayerRef
    drill_shape: Optional[DrillShape] = None
    drill_diameter: Optional[float] = None
    drill_slot_length: Optional[float] = None
    plated: Optional[bool] = True
    solder_mask_margin: Optional[float] = None
    paste_mask_margin: Optional[float] = None
    corner_radius_ratio: Optional[float] = None
    vertices: Optional[List[Point]] = None
    attributes: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_shape(cls, m):
        if (
            m.shape in {PadShape.RECTANGLE, PadShape.OVAL, PadShape.ROUNDRECT}
            and m.height is None
        ):
            raise ValueError("Height required for non-circular pads")
        if m.shape == PadShape.POLYGON and not m.vertices:
            raise ValueError("Vertices required for POLYGON")
        if m.shape == PadShape.ROUNDRECT and m.corner_radius_ratio is None:
            m.corner_radius_ratio = 0.1
        return m

    @model_validator(mode="after")
    def _validate_drill(cls, m):
        tht = m.pad_type in {PadType.THROUGH_HOLE, PadType.VIA}
        if tht:
            if m.drill_diameter is None:
                raise ValueError("drill_diameter required for THT/Via")
            if m.drill_shape is None:
                m.drill_shape = DrillShape.ROUND
            if m.drill_shape == DrillShape.OBLONG and m.drill_slot_length is None:
                raise ValueError("drill_slot_length required for OBLONG")
        else:
            if any([m.drill_diameter, m.drill_shape, m.drill_slot_length]):
                raise ValueError("Drill properties only allowed on THT/Via")
        return m


class Drill(BaseModel):
    position: Point
    shape: DrillShape = DrillShape.ROUND
    diameter: float
    slot_length: Optional[float] = None
    plated: bool = False
    layer: LayerRef

    @model_validator(mode="after")
    def _validate(cls, m):
        if m.shape == DrillShape.OBLONG and m.slot_length is None:
            raise ValueError("slot_length required for OBLONG")
        if m.shape == DrillShape.ROUND and m.slot_length is not None:
            raise ValueError("slot_length not allowed for ROUND")
        return m


class Model3D(BaseModel):
    uuid: Optional[UUID] = None
    offset: Point3D = Field(default_factory=lambda: Point3D(x=0, y=0, z=0))
    rotation: EulerRotation = Field(default_factory=lambda: EulerRotation())
    scale: Point3D = Field(default_factory=lambda: Point3D(x=1, y=1, z=1))


class Footprint(BaseElement):
    pads: List[Pad] = Field(default_factory=list)
    graphics: List[GraphicElement] = Field(default_factory=list)
    origin: Point = Field(default_factory=lambda: Point(x=0, y=0))
    height: float = 0
    width: float = 0
    version_str: str = DEFAULT_VERSION
    #     A version string consists of numbers separated by dots (e.g., 0.1 or 2024.06.21).
    # Each number segment must be an unsigned integer between 0 and 99,999.
    # There can be no more than 10 number segments in total.
    # Empty segments (like in 1..2) are not allowed.
    model_3d: Optional[Model3D] = None
    custom_attributes: Dict[str, str] = Field(default_factory=dict)

    # Source coordinate system offsets for alignment calculations
    source_offset_x: Optional[float] = (
        None  # Original source X offset (in source units)
    )
    source_offset_y: Optional[float] = (
        None  # Original source Y offset (in source units)
    )

    class Config:
        validate_assignment = True


# --- Alignment Calculator ---


class AlignmentCalculator:
    """Calculates alignment between footprint PNG images and physical measurements."""

    def calculate_alignment(
        self,
        footprint: "Footprint",
        coordinate_mapper: Callable[[float, float], Tuple[float, float]],
        reference_pad_numbers: Optional[List[str]] = None,
    ) -> FootprintAlignment:
        """
        Calculate alignment data between PNG image and physical footprint.

        Args:
            footprint: Parsed Footprint object with pad data
            coordinate_mapper: Function that converts (mm_x, mm_y) to (png_x, png_y)
            reference_pad_numbers: Specific pad numbers to use, or None to auto-select

        Returns:
            FootprintAlignment object with calculated reference points
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Using coordinate mapper for all transformations")

        # Determine reference pads
        if reference_pad_numbers is None:
            reference_pads = self.select_optimal_reference_pads(footprint)
        else:
            # Use specified pads with default corners
            reference_pads = [(num, "TL") for num in reference_pad_numbers[:2]]

        # Create alignment references
        reference_points = []
        for pad_num, corner in reference_pads:
            # Find the pad
            pad = None
            for p in footprint.pads:
                if p.number == pad_num:
                    pad = p
                    break

            if not pad:
                logger.warning(f"Pad {pad_num} not found in footprint")
                continue

            # Calculate corner position in mm
            corner_offsets = {
                "TL": (-pad.width / 2, -pad.height / 2),
                "TR": (pad.width / 2, -pad.height / 2),
                "BL": (-pad.width / 2, pad.height / 2),
                "BR": (pad.width / 2, pad.height / 2),
            }

            mm_corner_x = pad.position.x + corner_offsets[corner][0]
            mm_corner_y = pad.position.y + corner_offsets[corner][1]

            # Use the coordinate mapper to convert to PNG coordinates
            png_x, png_y = coordinate_mapper(mm_corner_x, mm_corner_y)

            reference_points.append(
                AlignmentReference(
                    pad_number=f"{pad_num}_{corner}",
                    source_x=png_x,
                    source_y=png_y,
                    target_x=mm_corner_x,
                    target_y=-mm_corner_y,  # Invert Y for LibrePCB Y-up convention
                )
            )

            logger.info(
                f"Reference: Pad {pad_num} {corner} - "
                f"PNG({png_x:.1f}, {png_y:.1f}) -> MM({mm_corner_x:.3f}, {-mm_corner_y:.3f})"
            )

        if len(reference_points) < 2:
            raise ValueError("Could not create at least 2 reference points")

        return FootprintAlignment(
            svg_to_png_scale=1.0,  # Scale factor is handled by coordinate_mapper
            reference_points=reference_points,
        )

    def select_optimal_reference_pads(
        self, footprint: "Footprint"
    ) -> List[Tuple[str, str]]:
        """
        Select two pads at opposite corners for optimal alignment accuracy.

        Returns:
            List of (pad_number, corner_position) tuples
        """
        if len(footprint.pads) < 2:
            # Not enough pads, just use what we have
            return [(pad.number, "TL") for pad in footprint.pads[:2]]

        # Build pad info with corners
        pad_info = {}
        for pad in footprint.pads:
            corners = {
                "TL": (pad.position.x - pad.width / 2, pad.position.y - pad.height / 2),
                "TR": (pad.position.x + pad.width / 2, pad.position.y - pad.height / 2),
                "BL": (pad.position.x - pad.width / 2, pad.position.y + pad.height / 2),
                "BR": (pad.position.x + pad.width / 2, pad.position.y + pad.height / 2),
            }
            pad_info[pad.number] = {"pad": pad, "corners": corners}

        # Find the pair of corners with maximum diagonal distance
        best_score = 0
        best_pair = None

        pad_list = list(pad_info.items())
        for i in range(len(pad_list)):
            for j in range(i + 1, len(pad_list)):
                pad1_num, pad1_info = pad_list[i]
                pad2_num, pad2_info = pad_list[j]

                # Try opposite corner combinations
                for corner1, corner2 in [
                    ("TL", "BR"),
                    ("TR", "BL"),
                    ("BL", "TR"),
                    ("BR", "TL"),
                ]:
                    x1, y1 = pad1_info["corners"][corner1]
                    x2, y2 = pad2_info["corners"][corner2]

                    # Calculate metrics
                    distance = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
                    x_spread = abs(x2 - x1)
                    y_spread = abs(y2 - y1)

                    # Favor good spread in both dimensions
                    spread_score = (
                        min(x_spread, y_spread) / max(x_spread, y_spread)
                        if max(x_spread, y_spread) > 0
                        else 0
                    )

                    # Combined score
                    score = distance * (1 + spread_score)

                    if score > best_score:
                        best_score = score
                        best_pair = [(pad1_num, corner1), (pad2_num, corner2)]

        return best_pair or [
            (footprint.pads[0].number, "TL"),
            (footprint.pads[1].number, "BR"),
        ]
