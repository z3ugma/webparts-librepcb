# librepcb_serializer.py

# Global imports
import os
import uuid as uuid_module  # To avoid conflict with our Pydantic UUID
from datetime import datetime
from typing import List, Tuple

from models.footprint import (  # Relative import if in a package; from footprint_model import ( # Or direct if in the same folder and you add to sys.path
    AssemblyType,
    Footprint,
    PadShape,
)
from models.graphics import Circle, Point, Polygon, Polyline
from models.layer import LayerRef, LayerType

# Local imports
from .s_expression import SExpSymbol, serialize_to_sexpr


class LibrePCBFootprintSerializer:
    def __init__(self, invert_y: bool = True):
        """
        Args:
            invert_y: If true, inverts Y coordinates (CDM Y-Down -> LibrePCB Y-Up).
                      Set to False if your CDM is already Y-Up relative to footprint origin.
        """
        self.invert_y = invert_y
        # This can be a fixed value or calculated if needed
        # For Y inversion, we flip around Y=0 of the footprint's local origin.
        # So, new_y = -old_y.

    def _transform_y(self, y: float) -> float:
        return -y if self.invert_y else y

    def _transform_point(self, point: Point) -> List:
        return [point.x, self._transform_y(point.y)]

    def _transform_shape(self, shape: PadShape) -> str:
        LIBREPCB_SHAPE_MAP = {
            PadShape.ROUNDRECT: "roundrect",
        }
        return SExpSymbol(LIBREPCB_SHAPE_MAP.get(shape, "roundrect"))

    def _transform_side(self, layer_ref: LayerRef) -> str:
        cdm_type = layer_ref.type
        LIBREPCB_SIDE_MAP = {
            LayerType.TOP_COPPER: "top",
        }
        return SExpSymbol(LIBREPCB_SIDE_MAP[cdm_type])

    def _transform_layer(self, layer_ref: LayerRef) -> str:
        cdm_type = layer_ref.type
        # bot_cu)
        # bot_legend)
        # bot_names)
        # bot_stop_mask)
        # brd_cutouts)
        # brd_documentation)
        # brd_guide)
        # brd_outlines)
        # sch_documentation)
        # sym_hidden_grab_areas)
        # sym_names)
        # sym_outlines)
        # sym_values)
        # top_courtyard)
        # top_cu)
        # top_documentation)
        # top_legend)
        # top_names)
        # top_package_outlines)
        # top_solder_paste)
        # top_stop_mask)
        # top_values)
        LIBREPCB_LAYER_MAP = {
            LayerType.ASSEMBLY_TOP: "top_legend",
            LayerType.DOCUMENTATION: "top_documentation",
            LayerType.COURTYARD_TOP: "top_courtyard",
            LayerType.TOP_SILKSCREEN: "top_legend",
            LayerType.TOP_PASTE_MASK: "top_stop_mask",
            LayerType.ASSEMBLY_TOP: "top_legend",
        }
        return SExpSymbol(LIBREPCB_LAYER_MAP[cdm_type])

    def serialize_circles(self, footprint: Footprint) -> List[Tuple]:
        #           (circle 84636231-61b2-4a07-9682-28a88ce99354 (layer top_legend)
        #    (width 0.2) (fill true) (grab_area false) (diameter 0.2) (position 96.52 -73.66)
        #   )
        polygons = [k for k in footprint.graphics if isinstance(k, Circle)]
        return [
            (
                "circle",
                [
                    uuid_module.uuid4(),
                    ("layer", [self._transform_layer(polygon.layer)]),
                    ("width", [polygon.stroke_width]),
                    ("fill", [True]),
                    ("grab_area", [False]),
                    ("position", self._transform_point(polygon.center)),
                    ("diameter", [polygon.radius * 2]),
                ],
            )
            for polygon in polygons
        ]

    def serialize_polylines(self, footprint: Footprint) -> List[Tuple]:
        polygons = [
            polygon for polygon in footprint.graphics if isinstance(polygon, Polyline)
        ]
        polygons = [polygon for polygon in polygons]
        return [
            (
                "polygon",
                [
                    uuid_module.uuid4(),
                    ("layer", [self._transform_layer(polygon.layer)]),
                    ("width", [polygon.stroke_width]),
                    ("fill", [False]),
                    ("grab_area", [False]),
                ]
                + [
                    #  (vertex (position 2.675 -2.535) (angle 0.0))
                    (
                        "vertex",
                        [("position", self._transform_point(vertex)), ("angle", [0])],
                    )
                    for vertex in polygon.points
                ],
            )
            for polygon in polygons
        ]

    def serialize_polygons(self, footprint: Footprint) -> List[Tuple]:
        polygons = [
            polygon for polygon in footprint.graphics if isinstance(polygon, Polygon)
        ]

        polygons = [
            p for p in polygons if p.layer != LayerRef(type=LayerType.TOP_PASTE_MASK)
        ]

        # Copy the courtyard into a Documentation polygon too
        for polygon in polygons:
            if polygon.layer == LayerRef(type=LayerType.COURTYARD_TOP):
                polygon.filled = False
                polygons.append(
                    Polygon(
                        layer=LayerRef(type=LayerType.DOCUMENTATION),
                        vertices=polygon.vertices,
                        stroke_width=0.1,
                        filled=False,
                    )
                )

        return [
            (
                "polygon",
                [
                    uuid_module.uuid4(),
                    ("layer", [self._transform_layer(polygon.layer)]),
                    ("width", [polygon.stroke_width]),
                    ("fill", [polygon.filled]),
                    ("grab_area", [False]),
                ]
                + [
                    (
                        "vertex",
                        [("position", self._transform_point(vertex)), ("angle", [0])],
                    )
                    for vertex in polygon.vertices
                ],
            )
            for polygon in polygons
        ]

    def add_name_value_labels(self, footprint: Footprint) -> List[Tuple]:
        y = footprint.height / 2 * 1.2

        #   (stroke_text 744036eb-348a-4eca-96a6-3bad20fe4aa5 (layer top_names)
        #    (height 1.0) (stroke_width 0.2) (letter_spacing auto) (line_spacing auto)
        #    (align center bottom) (position 0.0 4.08) (rotation 0.0)
        #    (auto_rotate true) (mirror false) (value "{{NAME}}")
        #   )
        #   (stroke_text 36adbd08-0cd2-4b53-a332-4da8451f6f1e (layer top_values)
        #    (height 1.0) (stroke_width 0.2) (letter_spacing auto) (line_spacing auto)
        #    (align center top) (position 0.0 -4.0) (rotation 0.0)
        #    (auto_rotate true) (mirror false) (value "{{VALUE}}")
        #   )
        return [
            (
                "stroke_text",
                [
                    uuid_module.uuid4(),
                    ("layer", ["top_names"]),
                    ("height", [1.0]),
                    ("stroke_width", [0.2]),
                    ("letter_spacing", [SExpSymbol("auto")]),
                    ("line_spacing", [SExpSymbol("auto")]),
                    ("align", [SExpSymbol("center"), SExpSymbol("bottom")]),
                    ("position", [0.0, y]),
                    ("rotation", [0.0]),
                    ("auto_rotate", [True]),
                    ("mirror", [False]),
                    ("value", ["{{NAME}}"]),
                ],
            ),
            (
                "stroke_text",
                [
                    uuid_module.uuid4(),
                    ("layer", ["top_values"]),
                    ("height", [1.0]),
                    ("stroke_width", [0.2]),
                    ("letter_spacing", [SExpSymbol("auto")]),
                    ("line_spacing", [SExpSymbol("auto")]),
                    ("align", [SExpSymbol("center"), SExpSymbol("top")]),
                    ("position", [0.0, -y]),
                    ("rotation", [0.0]),
                    ("auto_rotate", [True]),
                    ("mirror", [False]),
                    ("value", ["{{VALUE}}"]),
                ],
            ),
        ]

    def serialize_to_file(
        self, footprint: Footprint, dir_path: str, filename: str = "package.lp"
    ):
        """
        Serializes the Footprint to a LibrePCB package file (.lp) inside a specified directory.
        The directory `dir_path/<package_uuid>` will be created if it doesn't exist.
        """
        pkg_uuid = footprint.uuid if footprint.uuid else uuid_module.uuid4()

        modelcontent = None
        if footprint.model_3d:
            modelcontent = (
                "3d_model",
                [
                    footprint.model_3d.uuid,
                ],
            )

        footprint_contents = (
            [
                footprint.uuid,
                ("name", ["default"]),
                ("description", [""]),
                ("3d_position", [0, 0, 0]),
                ("3d_rotation", [0, 0, 0]),
                modelcontent,
            ]
            + [
                (
                    # {'attributes': {},
                    #  'corner_radius_ratio': 0.1,
                    #  'height': 0.034720403000000004,
                    #  'layer': LayerRef(type=<LayerType.TOP_COPPER: 'top_copper'>, index=None),
                    #  'number': '1',
                    #  'pad_type': <PadType.SMD: 'smd'>,
                    #  'paste_mask_margin': None,
                    #  'plated': None,
                    #  'position': Pt(15.375, 11.532),
                    #  'rotation': 0.0,
                    #  'shape': <PadShape.ROUNDRECT: 'roundrect'>,
                    #  'solder_mask_margin': None,
                    #  'start_layer': None,
                    #  'uuid': UUID('126138e2-d1cf-4ed3-8bfa-a62cb46c7516'),
                    #  'vertices': None,
                    #  'width': 0.103074597}
                    # (Pdb)
                    "pad",
                    [
                        uuid_module.uuid4(),
                        ("side", [self._transform_side(pad.layer)]),
                        ("shape", [self._transform_shape(pad.shape)]),
                        ("position", self._transform_point(pad.position)),
                        ("rotation", [0.0]),
                        ("size", [pad.width, pad.height]),
                        ("radius", [0.0]),
                        ("stop_mask", [SExpSymbol("auto")]),
                        ("solder_paste", [SExpSymbol("auto")]),
                        ("clearance", [0]),
                        ("function", [SExpSymbol("standard")]),
                        ("package_pad", [pad.uuid]),
                    ],
                )
                for pad in footprint.pads
            ]
            + self.serialize_polylines(footprint)
            + self.serialize_circles(footprint)
            + self.serialize_polygons(footprint)
            + self.add_name_value_labels(footprint)
        )

        modelcontent = None
        if footprint.model_3d:
            modelcontent = (
                "3d_model",
                [
                    footprint.model_3d.uuid,
                    ("name", [footprint.name]),
                ],
            )

        pkg = serialize_to_sexpr(
            "librepcb_package",
            [
                pkg_uuid,
                ("name", [footprint.name]),
                ("description", [footprint.description]),
                ("author", ["Fred Turkington"]),
                ("keywords", ["test, test2"]),
                ("generated_by", [""]),
                (
                    "category",
                    [uuid_module.UUID("1d2630f1-c375-49f0-a0dc-2446735d82f4")],
                ),
                ("assembly_type", [SExpSymbol(AssemblyType.SMT)]),
                ("version", ["0.1"]),
                ("created", [datetime(2024, 12, 27, 22, 45, 27)]),
                ("deprecated", [False]),
            ]
            + [("pad", [pad.uuid, ("name", [pad.number])]) for pad in footprint.pads]
            + [  # (3d_model 9a087b79-3270-479b-87ec-a8a5b0d67910 (name "C2040"))
                modelcontent,
                ("footprint", footprint_contents),
            ],
        )

        # Known good package
        """
        (librepcb_package fff4e0d1-ce87-4f52-b8eb-d21d4a3b69ce
            (name "Test")
            (description "Test")
            (keywords "test, test2")
            (author "Fred Turkington")
            (version "0.2")
            (created 2025-05-19T03:35:52Z)
            (deprecated false)
            (generated_by "")
            (category 1d2630f1-c375-49f0-a0dc-2446735d82f4)
            (assembly_type auto)
            (footprint c23ecccc-9706-4215-9828-1469f0fe8729
            (name "default")
            (description "")
            )
            )
        """

        # LibrePCB expects package files in <library_root>/pkg/<package_uuid>/package.lp
        # For simplicity, we'll just take a base `dir_path` and create the UUID subdir in it.
        # A full library structure would involve more.

        # This method assumes dir_path is the directory where the UUID-named folder should go.
        # e.g. dir_path = "/path/to/my_librepcb_library/pkg"
        # final_dir = "/path/to/my_librepcb_library/pkg/<package_uuid_str>"

        # For now, let's simplify and just save to dir_path/filename, assuming user handles UUID folder.
        # Or, save to dir_path/<package_uuid_str>/package.lp

        # For now, just save to the specified dir_path + filename
        # A more complete solution would create the pkg/<uuid>/ structure.
        # Example:
        # target_dir = os.path.join(dir_path, package_uuid_str)
        # os.makedirs(target_dir, exist_ok=True)
        # filepath = os.path.join(target_dir, filename)

        filepath = os.path.join(dir_path, filename)  # Simplified path for now

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(pkg)

        dotfilepath = os.path.join(dir_path, ".librepcb-pkg")
        with open(dotfilepath, "w", encoding="utf-8") as f:
            f.write("1\n")
        print(
            f"Footprint '{footprint.name}' serialized to LibrePCB package: {filepath}"
        )
