import rocketpy as rp
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import datetime

# --- Función auxiliar para obtener entrada numérica segura ---
def get_float_input(prompt, default_value):
    """Pide al usuario un valor flotante, con manejo de errores y valor por defecto."""
    while True:
        try:
            # Muestra el prompt con el valor por defecto
            value_str = input(f"{prompt} [{default_value}]: ")
            # Si el usuario solo presiona Enter, usa el valor por defecto
            if not value_str:
                return default_value
            return float(value_str)
        except ValueError:
            print("Entrada inválida. Por favor, ingrese un número.")

# --- VALORES POR DEFECTO ---
default_inclination = 90.0
default_heading = 0.0
default_rail_length = 1.2
default_cansat_mass = 0.3
default_drag_coeff = 0.6
default_burn_time = 2.0 
default_avg_thrust = 10.0
default_elevation = 20.0  

# --- SECCIÓN DE ENTRADA DEL USUARIO ---
print("--- Ingrese los parámetros de simulación (Presione Enter para usar el valor por defecto) ---")
user_inclination = get_float_input("Ángulo de lanzamiento (grados, 90=vertical)", default_inclination)
user_heading = get_float_input("Dirección de lanzamiento (Azimut, grados)", default_heading)
user_rail_length = get_float_input("Longitud de la rampa de lanzamiento (metros)", default_rail_length)
user_cansat_mass = get_float_input("Masa seca del CanSat (kg)", default_cansat_mass)
user_drag_coeff = get_float_input("Coeficiente de arrastre (simplificado)", default_drag_coeff)
user_burn_time = get_float_input("Duración del empuje del motor (segundos)", default_burn_time)
user_avg_thrust = get_float_input("Empuje promedio del motor (Newtons)", default_avg_thrust)
user_elevation = get_float_input("Elevación del sitio de lanzamiento (metros)", default_elevation)
print("-------------------------------------------------------------------------------------\n")

# --- Configuración del Entorno (usando la elevación del usuario) ---
env = rp.Environment(
    latitude=31.8664,
    longitude=-116.5959,
    elevation=user_elevation # <-- Usar valor del usuario
)
simulation_datetime = datetime.datetime(2025, 5, 3, 22, 52, 0) # Fecha fija por ahora
env.set_date(simulation_datetime, timezone="America/Tijuana")
env.set_atmospheric_model(type="standard_atmosphere")

# --- Definición del Motor (usando empuje y tiempo del usuario) ---
gas_motor = rp.SolidMotor(
    thrust_source=user_avg_thrust,       
    burn_time=user_burn_time,            
    dry_mass=0.5,                       
    dry_inertia=(0.02, 0.02, 0.001),     
    center_of_dry_mass_position=0.15,    
    grains_center_of_mass_position=0.2,  
    grain_number=1,                      
    grain_separation=0.005,              
    grain_density=1700.0,                
    grain_outer_radius=0.02,             
    grain_initial_inner_radius=0.005,    
    grain_initial_height=0.08,           
    nozzle_radius=0.01,                  
    throat_radius=0.005,                 
    interpolation_method='linear',
    nozzle_position=0.0,
    coordinate_system_orientation='nozzle_to_combustion_chamber'
)

# --- Definición del CanSat (usando masa y arrastre del usuario) ---
can_sat = rp.Rocket(
    radius=0.033,                        
    mass=user_cansat_mass,          
    inertia=(0.0001, 0.0001, 0.0002),   
    center_of_mass_without_motor=0.15,  
    coordinate_system_orientation='nose_to_tail',
    power_off_drag=user_drag_coeff,     
    power_on_drag=user_drag_coeff       
)

# Añadir motor al CanSat
motor_position_z = 0.3 
can_sat.add_motor(gas_motor, position=motor_position_z)

# --- Configuración del Vuelo (usando parámetros de lanzamiento del usuario) ---
flight = rp.Flight(
    rocket=can_sat,
    environment=env,
    rail_length=user_rail_length,     
    inclination=user_inclination,     
    heading=user_heading              
)

# --- Simulación ---
print("Ejecutando simulación con los parámetros ingresados...")

# --- Resultados y Graficación ---
print(f"\nSimulación completada. Accediendo a resultados...")
print(f"Altitud Máxima (Apogeo) alcanzada: {flight.apogee:.2f} m")

try:
    solution_array = np.array(flight.solution)
    if solution_array.size == 0:
        print("\nADVERTENCIA: La simulación no produjo resultados. Verifique los parámetros.")
        exit() 
except Exception as e:
     print(f"\nERROR al acceder a los resultados de la simulación: {e}")
     print("Puede que necesite llamar a flight.post_process() después de crear el objeto Flight.")

     exit()

# --- Gráficas 2D ---

plt.figure(figsize=(10, 8))
plt.subplot(2, 1, 1)
plt.plot(solution_array[:, 0], solution_array[:, 3], label="Altitud (z)")

plt.legend()
plt.subplot(2, 1, 2)
plt.plot(solution_array[:, 0], solution_array[:, 6], label="Velocidad Vertical (vz)")

plt.legend()
plt.tight_layout()

# --- Gráfica 3D ---

pos_x = solution_array[:, 1]
pos_y = solution_array[:, 2]
pos_z = solution_array[:, 3]
fig3d = plt.figure(figsize=(10, 8))
ax3d = fig3d.add_subplot(111, projection='3d')
ax3d.plot(pos_x, pos_y, pos_z, label='Trayectoria del CanSat')

ax3d.legend()
ax3d.grid(True)

# --- generar imagen de las graficas ---
generate_file_name_custom = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + '.png'
plt.savefig(generate_file_name_custom, dpi=300, bbox_inches='tight')

# --- Mostrar TODAS las gráficas ---
plt.show()