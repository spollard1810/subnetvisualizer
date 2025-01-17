import tkinter as tk
import tkinter.messagebox as messagebox
import ipaddress
import csv

class SubnetVisualizer:
    def __init__(self, master):
        self.master = master
        master.title("Subnet Visualizer")

        # Summary Address
        self.summary_frame = tk.Frame(master)
        self.summary_frame.pack(pady=10)

        tk.Label(self.summary_frame, text="Summary Address:").pack(side=tk.LEFT)
        self.summary_entry = tk.Entry(self.summary_frame)
        self.summary_entry.pack(side=tk.LEFT, padx=5)

        # Add Subnet
        self.add_subnet_frame = tk.Frame(master)
        self.add_subnet_frame.pack()

        tk.Label(self.add_subnet_frame, text="Subnet Label:").pack(side=tk.LEFT)
        self.subnet_label_entry = tk.Entry(self.add_subnet_frame)
        self.subnet_label_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(self.add_subnet_frame, text="Subnet:").pack(side=tk.LEFT)
        self.subnet_entry = tk.Entry(self.add_subnet_frame)
        self.subnet_entry.pack(side=tk.LEFT, padx=5)

        self.add_subnet_button = tk.Button(self.add_subnet_frame, text="Add Subnet", command=self.add_subnet)
        self.add_subnet_button.pack(side=tk.LEFT, padx=5)

        # Export Button
        self.export_button = tk.Button(master, text="Export to CSV", command=self.export_to_csv)
        self.export_button.pack(pady=5)

        # Visualization Canvas
        self.canvas = tk.Canvas(master, width=800, height=400, bg="lightgray")
        self.canvas.pack(pady=20)

        # Subnet List
        self.subnets = []

    def add_subnet(self):
        summary_address_str = self.summary_entry.get()
        subnet_label = self.subnet_label_entry.get()
        subnet_str = self.subnet_entry.get()

        try:
            summary_network = ipaddress.ip_network(summary_address_str, strict=False)
            subnet = ipaddress.ip_network(subnet_str, strict=False)
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid IP address or subnet: {e}")
            return

        if not summary_network.supernet_of(subnet):
            messagebox.showerror("Error", "Subnet is not within the summary address range.")
            return

        # Check for overlaps
        for existing_subnet in self.subnets:
            if existing_subnet['network'].overlaps(subnet):
                messagebox.showerror("Error", f"Subnet overlaps with existing subnet: {existing_subnet['label']}")
                return

        self.subnets.append({
            'label': subnet_label,
            'network': subnet
        })

        # Sort subnets by network address
        self.subnets.sort(key=lambda x: x['network'].network_address)

        self.subnet_label_entry.delete(0, tk.END)
        self.subnet_entry.delete(0, tk.END)
        self.visualize_subnets(summary_network)

    def visualize_subnets(self, summary_network):
        self.canvas.delete("all")

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        summary_bar_height = 30
        self.canvas.create_rectangle(0, 0, canvas_width, summary_bar_height, fill="blue", outline="black")
        self.canvas.create_text(10, summary_bar_height / 2, text=str(summary_network), anchor=tk.W, fill="white")

        total_addresses = summary_network.num_addresses
        start_y = summary_bar_height + 10
        current_address = summary_network.network_address  # Start at the beginning of the summary network

        for subnet in self.subnets:
            # Draw space between subnets if any
            if current_address < subnet['network'].network_address:
                gap_addresses = int(subnet['network'].network_address) - int(current_address)  # Convert to integer for subtraction
                gap_ratio = gap_addresses / total_addresses
                gap_height = (canvas_height - start_y - 20) * gap_ratio
                
                self.canvas.create_rectangle(10, start_y, canvas_width - 10, start_y + gap_height, fill="gray", outline="black")
                self.canvas.create_text(20, start_y + gap_height / 2, text=f"Available ({gap_addresses} addresses)", anchor=tk.W, fill="black")

                start_y += gap_height + 5

            # Draw subnet
            subnet_ratio = subnet['network'].num_addresses / total_addresses
            subnet_height = (canvas_height - start_y - 20) * subnet_ratio

            self.canvas.create_rectangle(10, start_y, canvas_width - 10, start_y + subnet_height, fill="green", outline="black")
            label_text = f"{subnet['label']} ({subnet['network']})"
            self.canvas.create_text(20, start_y + subnet_height / 2, text=label_text, anchor=tk.W, fill="white")

            start_y += subnet_height + 5
            current_address = subnet['network'].broadcast_address + 1  # Move to the next address after the current subnet

        # Draw remaining space at the end
        if current_address < summary_network.broadcast_address:
            remaining_addresses = int(summary_network.broadcast_address) - int(current_address) + 1
            remaining_ratio = remaining_addresses / total_addresses
            remaining_height = (canvas_height - start_y - 10) * remaining_ratio

            self.canvas.create_rectangle(10, start_y, canvas_width - 10, start_y + remaining_height, fill="gray", outline="black")
            self.canvas.create_text(20, start_y + remaining_height / 2, text=f"Available ({remaining_addresses} addresses)", anchor=tk.W, fill="black")

    def export_to_csv(self):
        if not self.subnets:
            messagebox.showwarning("Warning", "No subnets to export.")
            return

        try:
            with open("subnets.csv", "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Label", "Subnet", "Network Address", "Broadcast Address", "Number of Hosts"])  # Header row

                for subnet in self.subnets:
                    writer.writerow([
                        subnet['label'],
                        str(subnet['network']),
                        str(subnet['network'].network_address),
                        str(subnet['network'].broadcast_address),
                        subnet['network'].num_addresses - 2  # Usable hosts
                    ])

            messagebox.showinfo("Export Successful", "Subnet data exported to subnets.csv")

        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred during export: {e}")

root = tk.Tk()
app = SubnetVisualizer(root)
root.mainloop()