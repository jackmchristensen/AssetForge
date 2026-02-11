# Asset Forge

  A Blender addon that automates the asset export pipeline from Blender to Unreal Engine, with built-in validation and material setup.
  It validates your mesh assets, exports them to FBX with metadata, and prepares materials for streamlined Unreal ingestion.
  
   The goal is to reduce repetitive setup work, enforce consistent naming and asset standards, and catch common issues before assets reach the engine.

## Pipeline Overview
  
  1. **Validation**
  
  Asset Forge runs rule-based validation checks including:
    - UV map presence
    - Manifold geometry
    - Material configuration
    - Naming conventions
    - Texture dependencies
  Errors and warnings are reported directly in the Blender UI.

  2. **Export**

  Exports include:
    - FBX mesh data (with modifiers applied)
    - JSON metadata manifest containing:
      - Mesh statistics
      - Material and texture dependencies
      - Validation results
      - Export configuration

  3. **Unreal Import**

  Python script:
    - Imports FBX assets
    - Assigns textures to predefined material instance slots
    - Applies naming conventions
    - Reduces manual setup in engine
  Complex materials are intentionally preserved for manual refinement.

## Features

  - Rule-based validation system with configurable error/warning severity
  - Naming convention enforcement for meshes, materials, and textures
  - Material analysis for Principled BSDF shaders:
    - Constant values
    - Texture inputs
    - complex node detection
  - Texture classification with colorspace awareness
  - Asset type profiles (small props, hero props, modular pieces)
  - Automated Unreal import via Python scripting

## Installation

  ```bash
```
  cd /path/to/blender/5.0/scripts/addons/
  git clone https://github.com/jackmchristensen/AssetForge.git asset_forge
  ```
  ```

  Then:
  Open Blender → Preferences →  Add-ons → Search "Asset Forge" → Enable

  Or

  Download repo as zip

  Then:
  Open Blender → Preferences →  Add-ons → Install from Disk...

## Usage

  1. Select your mesh object
  2. Configure export settings (directories, asset type, naming prefixes)
  3. Click "Export to Unreal"
  4. Review validation results in the UI 
  5. Assets are automatically imported into your Unreal project

## Technical Details

  **Built with:**

  - Python 3.13
  - Blender 5.0+
  - Unreal Engine 5.x Python API

  **Material System**

  Asset Forge inspects Principled BSDF materials and extracts:

    - Texture dependencies
    - Basic parameter values
    - Shader complexity classification
  Material recreation is intentionally conservative to preserve artistic intent.
