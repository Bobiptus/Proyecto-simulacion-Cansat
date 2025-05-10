from flask import Flask, render_template_string
import rocketpy as rp
import numpy as np
import matplotlib

# MUY IMPORTANTE: Establecer el backend de Matplotlib a 'Agg'
# Esto permite que Matplotlib funcione sin una interfaz gráfica de usuario (GUI)
# Debe hacerse ANTES de importar pyplot.
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D # Para la gráfica 3D
import datetime
import io
import base64
import traceback # Para imprimir errores detallados

app = Flask(__name__)

# --- Función auxiliar para convertir figura de Matplotlib a cadena base64 ---
def fig_to_base64(fig):
    """Convierte una figura de Matplotlib a una cadena base64 PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig) # ¡Importante! Cierra la figura para liberar memoria.
    return img_base64

# --- Lógica de simulación y graficación adaptada de testCansatTerminal.py ---
def ejecutar_simulacion_y_graficar():
    """
    Ejecuta la simulación del CanSat con RocketPy usando valores por defecto
    y devuelve un string HTML con las gráficas incrustadas.
    """
    print("--- Iniciando simulación con valores por defecto ---")
    # Valores por defecto (tomados de tu script testCansatTerminal.py)
    default_inclination = 90.0
    default_heading = 0.0
    default_rail_length = 1.2
    default_cansat_mass = 0.3 # Masa seca en kg
    default_drag_coeff = 0.6
    default_burn_time = 2.0   # Segundos
    default_avg_thrust = 10.0 # Newtons
    default_elevation = 20.0  # Metros

    inclination = default_inclination
    heading = default_heading
    rail_length = default_rail_length
    cansat_mass = default_cansat_mass
    drag_coeff = default_drag_coeff
    burn_time = default_burn_time
    avg_thrust = default_avg_thrust
    elevation = default_elevation

    try:
        print("Configurando entorno...")
        # --- Configuración del Entorno ---
        env = rp.Environment(latitude=31.8664, longitude=-116.5959, elevation=elevation)
        simulation_datetime = datetime.datetime.now() # Usar fecha y hora actual
        env.set_date(simulation_datetime, timezone="America/Tijuana") # Ajusta tu zona horaria si es necesario
        env.set_atmospheric_model(type="standard_atmosphere")
        print("Entorno configurado.")

        print("Definiendo motor...")
        # --- Definición del Motor ---
        # Usaremos SolidMotor, que requiere más parámetros que solo la curva y el tiempo.
        # Estos son ejemplos, necesitarás ajustarlos a tu motor real si es posible.
        thrust_curve = [(0, avg_thrust), (burn_time, avg_thrust)]
        
        GasMotor = rp.SolidMotor(
            thrustSource=thrust_curve,
            burnOut=burn_time,
            grainNumber=1,
            grainDensity=1800, # kg/m^3 (valor de ejemplo para propelente sólido)
            grainOuterRadius=0.02, # 2 cm (ejemplo)
            grainInitialInnerRadius=0.005, # 0.5 cm (ejemplo)
            grainInitialHeight=0.05, # 5 cm (ejemplo)
            nozzleRadius=0.01, # 1 cm (ejemplo)
            throatRadius=0.005, # 0.5 cm (ejemplo)
            interpolationMethod="linear"
        )
        print(f"Motor '{GasMotor.tag}' creado con tiempo de quemado: {GasMotor.burnOutTime}s")

        print("Definiendo CanSat (Rocket)...")
        # --- Definición del CanSat (Rocket) ---
        cansat_radius = 0.066 / 2 # Diámetro 66mm (típico de lata)
        
        can_sat = rp.Rocket(
            motor=GasMotor,
            radius=cansat_radius,
            mass=cansat_mass, # Masa seca (sin propelente)
            # Inertia: (Ix, Iy, Iz) en kg*m^2. Estos son valores de ejemplo.
            # Para un cilindro sólido: Iz = 0.5*m*r^2, Ix = Iy = (1/12)*m*(3*r^2 + h^2)
            # Supongamos una altura de 0.115m (11.5 cm)
            inertia_Iz = 0.5 * cansat_mass * (cansat_radius**2),
            inertia_IxIy = (1/12) * cansat_mass * (3*(cansat_radius**2) + (0.115**2)),
            inertia=(inertia_IxIy, inertia_IxIy, inertia_Iz),
            distanceRocketNozzle=-0.0575, # Mitad de la altura (ejemplo, CM en el centro)
            distanceRocketPropellant=-0.0575, # (ejemplo, CM propelente en el centro del cohete)
            powerOffDrag=drag_coeff,
            powerOnDrag=drag_coeff
        )
        # Posición de los botones del riel [delantero, trasero] desde el CM del cohete.
        # Ejemplo: si el cohete mide 11.5cm, y los botones están en los extremos.
        can_sat.setRailButtons([0.115/2, -0.115/2])
        print(f"CanSat '{can_sat.tag}' creado.")

        print("Configurando y ejecutando simulación de vuelo...")
        # --- Configuración del Vuelo y Simulación ---
        flight = rp.Flight(
            rocket=can_sat,
            environment=env,
            rail_length=rail_length,
            inclination=inclination,
            heading=heading,
            #max_time=burn_time + 20 # Limitar tiempo de simulación para evitar corridas muy largas
        )
        # Acceder a un resultado como apogee usualmente dispara la simulación (post-processing)
        print(f"Altitud Máxima (Apogeo) alcanzada: {flight.apogee:.2f} m")

        # Verificar si hay datos en la solución
        if flight.solution is None or not hasattr(flight.solution, 'source_raw') or flight.solution.source_raw.shape[0] <= 1:
            # A veces, es necesario llamar explícitamente a post_process o puede que la simulación no haya tenido éxito
            if hasattr(flight, 'post_process'):
                print("Intentando flight.post_process() explícitamente...")
                flight.post_process() # Asegurar que se procesen todos los datos
            
            if flight.solution is None or not hasattr(flight.solution, 'source_raw') or flight.solution.source_raw.shape[0] <= 1:
                print("ADVERTENCIA: La simulación no produjo suficientes resultados en flight.solution.")
                apogee_val = flight.apogee if hasattr(flight, 'apogee') else 'No disponible'
                return f"<p>Error: La simulación no produjo resultados graficables. Apogeo: {apogee_val}</p>"

        solution_array = flight.solution.source_raw
        # Formato esperado de solution_array: [tiempo, x, y, z, vx, vy, vz, e0, e1, e2, e3, wx, wy, wz]
        # Índices:                        t:0, x:1, y:2, z:3, vx:4,vy:5,vz:6 ...

        if solution_array.size == 0 or solution_array.shape[0] <= 1:
            return f"<p>ADVERTENCIA: La simulación no produjo resultados válidos. Apogeo: {flight.apogee:.2f} m</p>"
        
        print("Generando gráficas...")
        # --- Preparar HTML para las imágenes ---
        img_html_output = f"<h2>Simulación Completada</h2><p>Apogeo (calculado por RocketPy): {flight.apogee:.2f} m</p>"
        
        # --- GRÁFICA 2D: Altitud vs Tiempo ---
        fig_alt, ax_alt = plt.subplots(figsize=(10, 6))
        # Usar directamente las funciones de RocketPy para plotear si es posible (más robusto)
        if hasattr(flight, 'z') and hasattr(flight.z, 'plot'):
            flight.z.plot(ax=ax_alt, label="Altitud (z vs t)") # Plotea Z contra el tiempo de la función Z
        else: # Fallback al array de solución
            ax_alt.plot(solution_array[:, 0], solution_array[:, 3], label="Altitud (z)")
        
        ax_alt.set_xlabel("Tiempo (s)")
        ax_alt.set_ylabel("Altitud (m)")
        ax_alt.set_title("Altitud del CanSat vs. Tiempo")
        ax_alt.legend()
        ax_alt.grid(True)
        
        img_base64_alt = fig_to_base64(fig_alt)
        img_html_output += f"<h3>Altitud vs Tiempo</h3><img src='data:image/png;base64,{img_base64_alt}' alt='Altitud vs Tiempo'>"

        # --- GRÁFICA 3D de Trayectoria ---
        if solution_array.shape[1] > 3: # Asegurarse que tenemos columnas x, y, z
            x_flight = solution_array[:, 1]
            y_flight = solution_array[:, 2]
            z_flight = solution_array[:, 3]

            fig3d = plt.figure(figsize=(10, 8))
            ax3d = fig3d.add_subplot(111, projection='3d')
            ax3d.plot(x_flight, y_flight, z_flight, label="Trayectoria del CanSat")
            ax3d.set_xlabel("Posición X (m)")
            ax3d.set_ylabel("Posición Y (m)")
            ax3d.set_zlabel("Posición Z (Altitud) (m)")
            ax3d.set_title("Trayectoria 3D del CanSat")
            ax3d.legend()
            plt.tight_layout() # Ajusta el padding
            
            img_base64_3d = fig_to_base64(fig3d)
            img_html_output += f"<h3>Trayectoria 3D</h3><img src='data:image/png;base64,{img_base64_3d}' alt='Trayectoria 3D'>"
        else:
            img_html_output += "<p>No hay suficientes datos en solution_array para la trayectoria 3D (se necesitan columnas para x, y, z).</p>"
        
        print("--- Simulación y graficación finalizadas exitosamente. ---")
        return img_html_output

    except Exception as e:
        print(f"ERROR CRÍTICO durante la simulación o graficación: {e}")
        error_details = traceback.format_exc()
        print(error_details)
        return f"<h2>Error en la Simulación</h2><p>Ha ocurrido un error:</p><pre>{e}</pre><pre>{error_details}</pre>"

# --- Ruta de la aplicación Flask ---
@app.route('/')
def home():
    # Llama a la función de simulación para obtener el HTML con las gráficas
    resultado_html = ejecutar_simulacion_y_graficar()
    
    # Plantilla HTML simple para mostrar los resultados
    html_template = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Simulación CanSat Sencilla con Flask</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            h1, h2, h3 {{ color: #333; }}
            img {{ 
                border: 1px solid #ddd; 
                margin-top: 10px; 
                margin-bottom: 20px; 
                max-width: 100%; 
                height: auto; 
                display: block;
            }}
            p {{ color: #555; }}
            pre {{ 
                background-color: #f4f4f4; 
                padding: 15px; 
                border: 1px solid #ccc; 
                overflow-x: auto; 
                white-space: pre-wrap; /* Permite que el texto se ajuste */
                word-wrap: break-word; /* Asegura que palabras largas no desborden */
            }}
            .container {{ max-width: 900px; margin: auto; padding: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Resultado de la Simulación del CanSat</h1>
            {resultado_html}
        </div>
    </body>
    </html>
    """
    return html_template

if __name__ == '__main__':
    print("Iniciando servidor Flask...")
    # app.run(debug=True) # debug=True es útil para desarrollo
    # Para que sea accesible en la red local (asegúrate de que tu firewall lo permite):
    app.run(host='0.0.0.0', port=5001, debug=True)
    print("Servidor Flask detenido.")