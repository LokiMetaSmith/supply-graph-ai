import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from src.core.utils.logging import get_logger
from .models.rfq import Bid
from .service import WeFlourishRFQService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/rfq", tags=["weflourish"])

# ---------------------------------------------------------------------------
# Models for Commercial Lifecycle
# ---------------------------------------------------------------------------

class BidCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ohm_id: str
    project_name: str
    description: str
    project_link: Optional[str] = None
    required_capabilities: List[str] = []
    metadata: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Models for RFQ Document Generation
# ---------------------------------------------------------------------------

class RFQSolutionInput(BaseModel):
    facility_id: str
    facility_name: str
    confidence: float
    score: float
    rank: int
    tree: Dict[str, Any]
    facility: Dict[str, Any]


class RFQGenerateRequest(BaseModel):
    okh_id: str
    okh_title: str
    okh_function: Optional[str] = None
    okh_version: Optional[str] = None
    quantity: int = 1
    okh_manifest: Optional[Dict[str, Any]] = None
    solutions: List[RFQSolutionInput]


class RFQDocument(BaseModel):
    rfq_number: str
    facility_name: str
    facility_id: str
    confidence: float
    rank: int
    quantity: int
    text: str
    okh_manifest: Optional[Dict[str, Any]] = None


class RFQGenerateResponse(BaseModel):
    timestamp: str
    data: Dict[str, Any]


# ---------------------------------------------------------------------------
# RFQ Templates & Rendering Logic
# ---------------------------------------------------------------------------

_TEMPLATE = """
REQUEST FOR QUOTATION (RFQ)
Date:         {date}
RFQ Number:   {rfq_number}
Valid Until:  {valid_until}

RECIPIENT (VENDOR)
  Name:         {facility_name}
{facility_contact_block}  Location:     {facility_location}

PROJECT INFORMATION
  Design Name:  {design_name}
  OKH ID:       {okh_id}
  Version:      {version}
  Function:     {function}
  License:      {license}
  Documentation: {repo_url}

{description_block}REQUIREMENTS
  Quantity:     {quantity} units
  Processes:    {process_list}
{dimensions_block}{quality_block}{materials_block}
MATCH DATA (INTERNAL REFERENCE)
{matched_capabilities_block}

TERMS AND CONDITIONS
  · This RFQ does not constitute a purchase order or commitment to buy.
  · All submitted pricing and technical information will be treated as
    confidential unless explicitly marked otherwise by the vendor.
  · The design is released under the license stated above; any manufacturing
    engagement is subject to compliance with those license terms.

Thank you for your consideration.
"""


def _rfq_number() -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    short = str(uuid.uuid4())[:8]
    return f"RFQ-{date_str}-{short}"


def _extract_location(facility: Dict[str, Any]) -> str:
    loc = facility.get("location", {})
    parts = [
        loc.get("city") or "",
        loc.get("country") or "",
    ]
    result = ", ".join(p for p in parts if p)
    return result or "Location not specified"


def _extract_contact_block(facility: Dict[str, Any]) -> str:
    contact = facility.get("contact", {})
    if not contact:
        return ""
    lines: List[str] = []
    if contact.get("contact_person"):
        lines.append(f"  Contact:      {contact['contact_person']}")
    if contact.get("name"):
        lines.append(f"  Organisation: {contact['name']}")
    if contact.get("website"):
        lines.append(f"  Website:      {contact['website']}")
    nested = contact.get("contact", {})
    if isinstance(nested, dict):
        if nested.get("landline"):
            lines.append(f"  Phone:        {nested['landline']}")
        if nested.get("mobile"):
            lines.append(f"  Mobile:       {nested['mobile']}")
    return ("\n".join(lines) + "\n") if lines else ""


def _cap_label(cap: str) -> str:
    if "wikipedia.org/wiki/" in cap:
        return cap.split("/wiki/")[-1].replace("_", " ").title()
    return cap


def _extract_processes_from_manifest(manifest: Optional[Dict[str, Any]]) -> str:
    if not manifest:
        return "See design documentation"
    procs = manifest.get("manufacturing_processes") or []
    if not procs:
        specs = manifest.get("manufacturing_specs") or {}
        procs = [
            r.get("process_name")
            for r in specs.get("process_requirements", [])
            if r.get("process_name")
        ]
    if not procs:
        return "See design documentation"
    return ", ".join(str(p) for p in procs)


def _extract_matched_capabilities_block(solution: RFQSolutionInput) -> str:
    tree = solution.tree
    lines: List[str] = []

    caps = tree.get("capabilities_used", [])
    if caps:
        cap_labels = [_cap_label(c) for c in caps if isinstance(c, str)]
        lines.append(f"  Matched processes:  {', '.join(cap_labels) or '—'}")

    lines.append(f"  Match confidence:   {round(solution.confidence * 100)}%")
    lines.append(f"  Match rank:         #{solution.rank}")

    missing = tree.get("missing_capabilities", [])
    if missing:
        missing_labels = [_cap_label(c) for c in missing if isinstance(c, str)]
        lines.append(f"  Unmet requirements: {', '.join(missing_labels)}")
        lines.append(
            "  Note: Please advise whether the unmet requirements above can be"
        )
        lines.append("        accommodated through partnerships or subcontracting.")
    else:
        lines.append("  All required capabilities matched.")

    return "\n".join(lines)


def _extract_manifest_extras(
    manifest: Optional[Dict[str, Any]],
    solution: Optional[RFQSolutionInput] = None,
) -> Dict[str, str]:
    if not manifest:
        return {
            "license": "—",
            "repo_url": "—",
            "description_block": "",
            "dimensions_block": "",
            "quality_block": "",
            "materials_block": "",
            "matched_capabilities_block": "  See match data.",
        }

    license_info = manifest.get("license", {})
    if isinstance(license_info, dict):
        hw = license_info.get("hardware") or license_info.get("documentation") or "—"
    else:
        hw = str(license_info) if license_info else "—"

    repo_url = manifest.get("repo") or manifest.get("documentation_home") or "—"

    desc = manifest.get("description") or manifest.get("intended_use") or ""
    description_block = (f"  Description:  {desc}\n") if desc else ""

    specs = manifest.get("manufacturing_specs") or {}
    dims = specs.get("outer_dimensions")
    if dims and isinstance(dims, dict):
        w = dims.get("width") or dims.get("x")
        h = dims.get("height") or dims.get("y")
        d = dims.get("depth") or dims.get("z") or dims.get("thickness")
        unit = dims.get("unit", "mm")
        parts_dim = [f"{v} {unit}" for v in [w, h, d] if v is not None]
        dimensions_block = (
            f"  Dimensions:   {' × '.join(parts_dim)}\n" if parts_dim else ""
        )
    else:
        dimensions_block = ""

    quality_stds = specs.get("quality_standards") or []
    if quality_stds:
        quality_block = f"  Quality:      {', '.join(str(q) for q in quality_stds)}\n"
    else:
        quality_block = "  Quality:      Per standard good manufacturing practice\n"

    materials = manifest.get("materials") or []
    mat_names: List[str] = []
    for m in materials:
        if isinstance(m, dict):
            name = m.get("name") or m.get("material_id") or ""
            if name:
                mat_names.append(name)
        elif isinstance(m, str):
            mat_names.append(m)
    materials_block = (f"  Materials:    {', '.join(mat_names)}\n") if mat_names else ""

    if solution is not None:
        matched_capabilities_block = _extract_matched_capabilities_block(solution)
    else:
        matched_capabilities_block = "  See match data."

    return {
        "license": hw,
        "repo_url": repo_url,
        "description_block": description_block,
        "dimensions_block": dimensions_block,
        "quality_block": quality_block,
        "materials_block": materials_block,
        "matched_capabilities_block": matched_capabilities_block,
    }


def _render_rfq(
    *,
    solution: RFQSolutionInput,
    okh_title: str,
    okh_id: str,
    okh_function: Optional[str],
    okh_version: Optional[str],
    quantity: int,
    okh_manifest: Optional[Dict[str, Any]] = None,
) -> str:
    extras = _extract_manifest_extras(okh_manifest, solution)
    now = datetime.now()
    valid_until = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    return _TEMPLATE.format(
        date=now.strftime("%Y-%m-%d"),
        rfq_number=_rfq_number(),
        valid_until=valid_until,
        facility_name=solution.facility_name,
        facility_contact_block=_extract_contact_block(solution.facility),
        facility_location=_extract_location(solution.facility),
        design_name=okh_title,
        okh_id=okh_id,
        version=okh_version or "—",
        function=okh_function or "See design documentation",
        license=extras["license"],
        repo_url=extras["repo_url"],
        description_block=extras["description_block"],
        process_list=_extract_processes_from_manifest(okh_manifest),
        dimensions_block=extras["dimensions_block"],
        quality_block=extras["quality_block"],
        materials_block=extras["materials_block"],
        matched_capabilities_block=extras["matched_capabilities_block"],
        quantity=quantity,
    )


# ---------------------------------------------------------------------------
# Commercial Lifecycle Endpoints
# ---------------------------------------------------------------------------

@router.post("/webhooks/weflourish", status_code=status.HTTP_200_OK)
async def weflourish_webhook(
    request: Request,
    x_weflourish_signature: str = Header(None),
    rfq_service: WeFlourishRFQService = Depends(WeFlourishRFQService.get_instance),
):
    body = await request.body()

    if not x_weflourish_signature:
        logger.warning("Missing x-weflourish-signature header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature",
        )

    if not rfq_service.verify_signature(body, x_weflourish_signature):
        logger.error("Invalid x-weflourish-signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    payload = await request.json()
    logger.info(f"Received WeFlourish webhook: {payload.get('event')}")

    await rfq_service.handle_webhook(payload)

    return {"status": "accepted"}


@router.post("/bids", status_code=status.HTTP_201_CREATED)
async def create_bid(
    bid_request: BidCreateRequest = Body(..., embed=True),
    rfq_service: WeFlourishRFQService = Depends(WeFlourishRFQService.get_instance),
):
    bid = Bid(
        ohm_id=bid_request.ohm_id,
        project_name=bid_request.project_name,
        description=bid_request.description,
        project_link=bid_request.project_link,
        required_capabilities=bid_request.required_capabilities,
        metadata=bid_request.metadata,
    )

    success = await rfq_service.create_bid_on_weflourish(bid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to push bid to WeFlourish",
        )

    return {
        "status": "success",
        "weflourish_id": bid.external_id,
        "ohm_id": bid.ohm_id
    }


# ---------------------------------------------------------------------------
# RFQ Document Generation Endpoint
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=RFQGenerateResponse)
async def generate_rfq(request: RFQGenerateRequest) -> RFQGenerateResponse:
    logger.info(
        f"Generating RFQs for okh_id={request.okh_id} "
        f"({len(request.solutions)} solution(s), qty={request.quantity})"
    )

    rfqs: List[RFQDocument] = []
    for sol in request.solutions:
        rfq_num = _rfq_number()
        text = _render_rfq(
            solution=sol,
            okh_title=request.okh_title,
            okh_id=request.okh_id,
            okh_function=request.okh_function,
            okh_version=request.okh_version,
            quantity=request.quantity,
            okh_manifest=request.okh_manifest,
        )
        rfqs.append(
            RFQDocument(
                rfq_number=rfq_num,
                facility_name=sol.facility_name,
                facility_id=sol.facility_id,
                confidence=sol.confidence,
                rank=sol.rank,
                quantity=request.quantity,
                text=text,
                okh_manifest=request.okh_manifest,
            )
        )

    return RFQGenerateResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={
            "rfqs": rfqs,
            "total_rfqs": len(rfqs),
            "okh_id": request.okh_id,
            "okh_title": request.okh_title,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
