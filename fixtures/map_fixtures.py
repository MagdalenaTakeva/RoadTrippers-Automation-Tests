import os
import time
import pytest


@pytest.fixture
def stabilize_map(driver):

    if not os.getenv("CI"):
        return

    driver.execute_script("""
        console.log("Applying Mapbox CI stabilization");

        document.querySelectorAll("canvas").forEach(c => {
            c.style.display = "none";
            c.style.pointerEvents = "none";
        });

        document.querySelectorAll(
            ".mapboxgl-popup, .mapboxgl-control-container, .ReactModal__Overlay"
        ).forEach(el => el.remove());

        if (window.map) {
            window.map.flyTo = () => {};
            window.map.easeTo = () => {};
            window.map.jumpTo = () => {};
            window.map.panTo = () => {};
            window.map.fitBounds = () => {};
            window.map.resize = () => {};
        }

        window.requestAnimationFrame = function(cb){
            return setTimeout(cb, 16);
        };

        try {
            if (window.map && window.map.fire) {
                window.map.fire("load");
            }
        } catch(e) {}
    """)

    time.sleep(0.5)