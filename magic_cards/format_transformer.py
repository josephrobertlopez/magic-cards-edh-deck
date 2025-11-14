"""Format transformer module for converting files to PDF."""

import subprocess
import os
from pathlib import Path


def transform_to_pdf(source_path, output_dir):
    """
    Convert file to PDF using LibreOffice.
    
    Args:
        source_path: Path to source file (e.g., PPTX)
        output_dir: Directory for output PDF file
        
    Returns:
        Path to generated PDF file, or None if conversion failed
    """
    print(f"📄 Converting to PDF...")
    print(f"  📥 Source: {source_path}")
    print(f"  📂 Output dir: {output_dir}")
    
    # Ensure paths are absolute
    source_path = Path(source_path).resolve()
    output_dir = Path(output_dir).resolve()
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if source exists
    if not source_path.exists():
        print(f"  ❌ Source file not found: {source_path}")
        return None
    
    try:
        # Try to find LibreOffice executable
        libreoffice_cmds = [
            'libreoffice',
            'soffice',
            '/usr/bin/libreoffice',
            '/usr/bin/soffice',
            '/Applications/LibreOffice.app/Contents/MacOS/soffice'
        ]
        
        libreoffice_path = None
        for cmd in libreoffice_cmds:
            try:
                result = subprocess.run(
                    [cmd, '--version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    libreoffice_path = cmd
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        if not libreoffice_path:
            print("  ❌ LibreOffice not found - please install LibreOffice")
            raise FileNotFoundError("LibreOffice executable not found")
        
        print(f"  🔧 Using: {libreoffice_path}")
        
        # Convert to PDF using LibreOffice headless mode
        command = [
            libreoffice_path,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', str(output_dir),
            str(source_path)
        ]
        
        print(f"  ⚙️  Converting...")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"  ❌ Conversion failed")
            print(f"  stderr: {result.stderr}")
            return None
        
        # Find generated PDF
        source_stem = source_path.stem
        pdf_path = output_dir / f"{source_stem}.pdf"
        
        # LibreOffice sometimes uses "output.pdf" as default name
        if not pdf_path.exists():
            pdf_path = output_dir / "output.pdf"
        
        if pdf_path.exists():
            print(f"  ✅ PDF created: {pdf_path}")
            return str(pdf_path)
        else:
            print(f"  ❌ PDF file not found after conversion")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"  ❌ Conversion timed out (60 seconds)")
        return None
    except Exception as e:
        print(f"  ❌ Error during conversion: {e}")
        return None
